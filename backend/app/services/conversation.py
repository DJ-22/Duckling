from __future__ import annotations
from datetime import datetime, timezone
from ..db import repo
from ..db.client import SupabaseRest
from . import grader, persona, retrieval, student

RETRIEVE_K = 5


class ConceptNotFound(Exception):
    pass


class SessionNotFound(Exception):
    pass


class SessionClosed(Exception):
    pass


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _running_explanation(transcript: list[dict], new_text: str) -> str:
    # The grade judges the fuller explanation built across turns, not just the
    # latest reply, so coverage accumulates as the user fills the gaps.
    prior = " ".join(turn["user"] for turn in transcript)
    return f"{prior} {new_text}".strip()


def _comprehension(transcript: list[dict]) -> int:
    total = sum(turn["grade"].get("student_comprehension_delta", 0) for turn in transcript)
    return min(100, max(0, total))


def _felt(session: dict) -> int | None:
    return (session.get("results") or {}).get("felt")


def _view(session: dict, concept: dict) -> dict:
    transcript = session.get("transcript") or []
    comprehension = _comprehension(transcript)
    return {
        "id": session["id"],
        "concept_id": session["concept_id"],
        "concept_name": concept["name"],
        "status": session["status"],
        "comprehension": comprehension,
        "student_state": student.comprehension_to_state(comprehension),
        "felt": _felt(session),
        "transcript": transcript,
    }


async def start_session(
    db: SupabaseRest, *, user_id: str, concept_id: str, felt: int | None = None
) -> dict:
    concept = await repo.get_owned_concept(db, concept_id)
    if concept is None:
        raise ConceptNotFound(concept_id)
    # Resume the existing open session for this concept rather than forking a new one;
    # a resumed session keeps its original felt rating.
    existing = await repo.find_in_progress_session(db, concept_id)
    session = existing or await repo.create_session(
        db, user_id=user_id, concept_id=concept_id, felt=felt
    )
    return _view(session, concept)


async def get_session(db: SupabaseRest, *, session_id: str) -> dict:
    session = await repo.get_owned_session(db, session_id)
    if session is None:
        raise SessionNotFound(session_id)
    concept = await repo.get_owned_concept(db, session["concept_id"])
    if concept is None:
        raise ConceptNotFound(session["concept_id"])
    return _view(session, concept)


async def add_turn(db: SupabaseRest, *, session_id: str, explanation: str) -> dict:
    session = await repo.get_owned_session(db, session_id)
    if session is None:
        raise SessionNotFound(session_id)
    if session["status"] != "in_progress":
        raise SessionClosed(session_id)

    concept = await repo.get_owned_concept(db, session["concept_id"])
    if concept is None:
        raise ConceptNotFound(session["concept_id"])

    transcript = session.get("transcript") or []
    full_explanation = _running_explanation(transcript, explanation)

    chunks = await retrieval.retrieve(
        db, subject_id=concept["subject_id"], query=full_explanation, k=RETRIEVE_K
    )
    grade = await grader.grade(
        explanation=full_explanation,
        concept_name=concept["name"],
        rubric=concept["rubric"],
        source_chunks=[chunk["content"] for chunk in chunks],
    )

    uncovered = [point.point for point in grade.coverage if not point.covered]
    question = await persona.ask_followup(
        concept_name=concept["name"],
        weakest_gap=grade.weakest_gap,
        uncovered_points=uncovered,
        explanation=explanation,
    )

    transcript.append({"user": explanation, "grade": grade.model_dump(), "student": question})
    await repo.save_transcript(db, session_id, transcript, _now())

    comprehension = _comprehension(transcript)
    return {
        "turn_index": len(transcript) - 1,
        "question": question,
        "overall": grade.overall,
        "delta": grade.student_comprehension_delta,
        "comprehension": comprehension,
        "student_state": student.comprehension_to_state(comprehension),
        "weakest_gap": grade.weakest_gap,
    }


async def complete_session(db: SupabaseRest, *, session_id: str) -> dict:
    session = await repo.get_owned_session(db, session_id)
    if session is None:
        raise SessionNotFound(session_id)
    concept = await repo.get_owned_concept(db, session["concept_id"])
    if concept is None:
        raise ConceptNotFound(session["concept_id"])

    transcript = session.get("transcript") or []
    final_overall = transcript[-1]["grade"]["overall"] if transcript else 0
    felt = _felt(session)

    results = {
        "comprehension": _comprehension(transcript),
        "final_overall": final_overall,
        "felt": felt,
        "understanding_map": [
            {
                "concept_id": session["concept_id"],
                "concept_name": concept["name"],
                "felt": felt,
                "shown": final_overall,
            }
        ],
    }
    await repo.complete_session(db, session_id, results, _now())
    return results
