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
