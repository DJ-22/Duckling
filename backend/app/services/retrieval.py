from __future__ import annotations
from ..db import repo
from ..db.client import SupabaseRest
from . import embeddings


async def retrieve(
    db: SupabaseRest, *, subject_id: str, query: str, k: int = 5
) -> list[dict]:
    query_embedding = embeddings.embed_text(query)
    return await repo.match_chunks(
        db, query_embedding=query_embedding, subject_id=subject_id, k=k
    )
