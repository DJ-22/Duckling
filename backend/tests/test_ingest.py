from __future__ import annotations
import pytest
from app.services import embeddings
from app.services.ingest import (
    MAX_UPLOAD_BYTES,
    UploadValidationError,
    chunk_text,
    content_hash,
    parse_document,
    validate_upload,
)


def test_validate_accepts_whitelisted_types():
    for name in ("notes.pdf", "syllabus.TXT", "chapter.md", "essay.docx"):
        validate_upload(name, 1024)


def test_validate_rejects_unlisted_type():
    with pytest.raises(UploadValidationError):
        validate_upload("malware.exe", 1024)


def test_validate_rejects_empty_and_oversize():
    with pytest.raises(UploadValidationError):
        validate_upload("notes.pdf", 0)
    with pytest.raises(UploadValidationError):
        validate_upload("notes.pdf", MAX_UPLOAD_BYTES + 1)


def test_parse_txt_and_md_from_bytes():
    assert parse_document("a.txt", b"hello world") == "hello world"
    assert parse_document("a.md", "# Title\n\nbody".encode()) == "# Title\n\nbody"


def test_content_hash_is_stable_and_content_addressed():
    assert content_hash(b"abc") == content_hash(b"abc")
    assert content_hash(b"abc") != content_hash(b"abd")


def test_chunk_respects_max_and_overlaps():
    text = " ".join(f"word{i}" for i in range(400))
    chunks = chunk_text(text, max_chars=200, overlap=40)
    assert len(chunks) > 1
    assert all(len(c) <= 200 for c in chunks)
    # consecutive chunks share trailing/leading words.
    first_tail = set(chunks[0].split()[-3:])
    assert first_tail & set(chunks[1].split())


def test_chunk_empty_text_is_empty():
    assert chunk_text("   ") == []


def test_embedding_dimension_and_normalization():
    vector = embeddings.embed_text("a short passage about photosynthesis")
    assert len(vector) == embeddings.EMBEDDING_DIM
    norm = sum(component * component for component in vector) ** 0.5
    assert norm == pytest.approx(1.0, abs=1e-3)
