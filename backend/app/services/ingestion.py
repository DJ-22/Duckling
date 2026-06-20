from __future__ import annotations
import secrets
from pathlib import Path
from ..db import repo
from ..db.client import SupabaseRest, to_pgvector
from ..schemas.sources import IngestResult
from . import embeddings, extractor
from .ingest import chunk_text, content_hash, parse_document


class SubjectNotFound(Exception):
    pass


async def ingest_source(
    db: SupabaseRest, *, user_id: str, subject_id: str, filename: str, data: bytes
) -> IngestResult:
    if await repo.get_owned_subject(db, subject_id) is None:
        raise SubjectNotFound(subject_id)

    digest = content_hash(data)
    if existing := await repo.find_source_by_hash(db, subject_id, digest):
        # Idempotent: identical bytes already ingested for this subject, so the
        # expensive parse/embed/extract is skipped.
        return IngestResult(source_id=existing["id"], chunks=0, concepts=0, cached=True)

    text = parse_document(filename, data)
    chunks = chunk_text(text)

    storage_path = f"{user_id}/{secrets.token_hex(16)}{Path(filename).suffix.lower()}"
    source = await repo.insert_source(
        db,
        user_id=user_id,
        subject_id=subject_id,
        filename=filename,
        content_hash=digest,
        storage_path=storage_path,
    )
    source_id = source["id"]

    if chunks:
        vectors = embeddings.embed_texts(chunks)
        await repo.insert_chunks(
            db,
            [
                {
                    "source_id": source_id,
                    "subject_id": subject_id,
                    "user_id": user_id,
                    "content": content,
                    "embedding": to_pgvector(vector),
                }
                for content, vector in zip(chunks, vectors)
            ],
        )

    concepts = await _extract_and_cache(db, user_id, subject_id, digest, text)
    return IngestResult(
        source_id=source_id, chunks=len(chunks), concepts=concepts, cached=False
    )


async def _extract_and_cache(
    db: SupabaseRest, user_id: str, subject_id: str, source_hash: str, text: str
) -> int:
    if await repo.get_concepts_by_hash(db, subject_id, source_hash):
        return 0

    extraction = await extractor.extract_concepts(text)
    if not extraction.concepts:
        return 0

    rows = [
        {
            "user_id": user_id,
            "subject_id": subject_id,
            "name": concept.name,
            "rubric": concept.rubric.model_dump(),
            "source_hash": source_hash,
        }
        for concept in extraction.concepts
    ]
    await repo.insert_concepts(db, rows)
    return len(rows)
