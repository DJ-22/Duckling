from __future__ import annotations
from .client import SupabaseRest, to_pgvector


async def get_owned_subject(db: SupabaseRest, subject_id: str) -> dict | None:
    rows = await db.select(
        "subjects", params={"id": f"eq.{subject_id}", "select": "id,user_id,name"}
    )
    return rows[0] if rows else None


async def find_source_by_hash(db: SupabaseRest, subject_id: str, content_hash: str) -> dict | None:
    rows = await db.select(
        "sources",
        params={
            "subject_id": f"eq.{subject_id}",
            "content_hash": f"eq.{content_hash}",
            "select": "id",
        },
    )
    return rows[0] if rows else None


async def insert_source(
    db: SupabaseRest,
    *,
    user_id: str,
    subject_id: str,
    filename: str,
    content_hash: str,
    storage_path: str,
) -> dict:
    rows = await db.insert(
        "sources",
        {
            "user_id": user_id,
            "subject_id": subject_id,
            "filename": filename,
            "content_hash": content_hash,
            "storage_path": storage_path,
        },
    )
    return rows[0]


async def insert_chunks(db: SupabaseRest, rows: list[dict]) -> None:
    if rows:
        await db.insert("chunks", rows, returning=False)


async def get_concepts_by_hash(db: SupabaseRest, subject_id: str, source_hash: str) -> list[dict]:
    return await db.select(
        "concepts",
        params={
            "subject_id": f"eq.{subject_id}",
            "source_hash": f"eq.{source_hash}",
            "select": "id,name",
        },
    )


async def insert_concepts(db: SupabaseRest, rows: list[dict]) -> list[dict]:
    return await db.insert("concepts", rows)


async def match_chunks(
    db: SupabaseRest, *, query_embedding: list[float], subject_id: str, k: int
) -> list[dict]:
    return await db.rpc(
        "match_chunks",
        {
            "query_embedding": to_pgvector(query_embedding),
            "match_subject_id": subject_id,
            "match_count": k,
        },
    )


async def get_owned_concept(db: SupabaseRest, concept_id: str) -> dict | None:
    rows = await db.select(
        "concepts",
        params={"id": f"eq.{concept_id}", "select": "id,subject_id,name,rubric"},
    )
    return rows[0] if rows else None


async def find_in_progress_session(db: SupabaseRest, concept_id: str) -> dict | None:
    rows = await db.select(
        "sessions",
        params={
            "concept_id": f"eq.{concept_id}",
            "status": "eq.in_progress",
            "select": "id,concept_id,status,transcript",
            "limit": "1",
        },
    )
    return rows[0] if rows else None


async def create_session(db: SupabaseRest, *, user_id: str, concept_id: str) -> dict:
    rows = await db.insert(
        "sessions", {"user_id": user_id, "concept_id": concept_id, "status": "in_progress"}
    )
    return rows[0]


async def get_owned_session(db: SupabaseRest, session_id: str) -> dict | None:
    rows = await db.select(
        "sessions",
        params={"id": f"eq.{session_id}", "select": "id,concept_id,status,transcript"},
    )
    return rows[0] if rows else None


async def save_transcript(
    db: SupabaseRest, session_id: str, transcript: list[dict], updated_at: str
) -> None:
    await db.update(
        "sessions",
        params={"id": f"eq.{session_id}"},
        values={"transcript": transcript, "updated_at": updated_at},
        returning=False,
    )


async def complete_session(
    db: SupabaseRest, session_id: str, results: dict, completed_at: str
) -> dict:
    rows = await db.update(
        "sessions",
        params={"id": f"eq.{session_id}"},
        values={
            "status": "completed",
            "results": results,
            "completed_at": completed_at,
            "updated_at": completed_at,
        },
    )
    return rows[0]
