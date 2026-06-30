from __future__ import annotations
from datetime import datetime, timezone
from .. import srs
from ..db import repo
from ..db.client import SupabaseRest


def _parse(ts: str | None) -> datetime | None:
    return datetime.fromisoformat(ts) if ts else None


async def get_dashboard(db: SupabaseRest, *, user_id: str) -> dict:
    now = datetime.now(timezone.utc)
    subjects = await repo.list_subjects(db)
    mastery_rows = await repo.list_mastery(db)
    open_sessions = await repo.list_in_progress_sessions(db)
    completed = await repo.list_completed_session_dates(db)

    mastery: list[dict] = []
    due: list[dict] = []
    for row in mastery_rows:
        concept = row.get("concepts") or {}
        next_review = _parse(row.get("next_review"))
        entry = {
            "concept_id": row["concept_id"],
            "concept_name": concept.get("name", ""),
            "subject_id": concept.get("subject_id"),
            "comprehension": srs.decay_comprehension(row["comprehension"], next_review, now),
            "next_review": row.get("next_review"),
        }
        mastery.append(entry)
        if next_review is not None and next_review <= now:
            due.append(entry)

    in_progress = [
        {
            "id": session["id"],
            "concept_id": session["concept_id"],
            "concept_name": (session.get("concepts") or {}).get("name", ""),
            "updated_at": session.get("updated_at"),
        }
        for session in open_sessions
    ]

    practiced_days = [
        parsed.astimezone(timezone.utc).date()
        for session in completed
        if (parsed := _parse(session.get("completed_at"))) is not None
    ]
    streak = srs.compute_streak(practiced_days, now.date())

    return {
        "subjects": subjects,
        "mastery": mastery,
        "due": due,
        "in_progress": in_progress,
        "streak": streak,
    }
