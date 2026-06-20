from __future__ import annotations
import hashlib
import io
from pathlib import Path
import pdfplumber
from docx import Document

ALLOWED_EXTENSIONS = {".pdf", ".txt", ".md", ".docx"}
MAX_UPLOAD_BYTES = 20 * 1024 * 1024


class UploadValidationError(ValueError):
    """Raised when an upload is the wrong type or size — surfaced to the client
    as a 4xx, never as a parser crash."""


def validate_upload(filename: str, size_bytes: int) -> str:
    extension = Path(filename).suffix.lower()
    if extension not in ALLOWED_EXTENSIONS:
        raise UploadValidationError(f"unsupported file type: {extension or 'none'}")
    if size_bytes <= 0:
        raise UploadValidationError("empty file")
    if size_bytes > MAX_UPLOAD_BYTES:
        raise UploadValidationError(f"file exceeds {MAX_UPLOAD_BYTES} byte limit")
    return extension


def content_hash(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def parse_document(filename: str, data: bytes) -> str:
    extension = Path(filename).suffix.lower()
    if extension == ".pdf":
        return _parse_pdf(data)
    if extension == ".docx":
        return _parse_docx(data)
    if extension in (".txt", ".md"):
        return data.decode("utf-8", errors="replace")
    raise UploadValidationError(f"unsupported file type: {extension or 'none'}")


def _parse_pdf(data: bytes) -> str:
    with pdfplumber.open(io.BytesIO(data)) as pdf:
        pages = [page.extract_text() or "" for page in pdf.pages]
    return "\n\n".join(pages)


def _parse_docx(data: bytes) -> str:
    document = Document(io.BytesIO(data))
    return "\n\n".join(p.text for p in document.paragraphs)


def chunk_text(text: str, *, max_chars: int = 1000, overlap: int = 150) -> list[str]:
    """Pack text into word-bounded chunks of at most max_chars, each sharing about
    `overlap` trailing characters with the next so a point split across a boundary
    still appears whole in one chunk."""
    if overlap >= max_chars:
        raise ValueError("overlap must be smaller than max_chars")

    words = text.split()
    if not words:
        return []

    chunks: list[str] = []
    current: list[str] = []
    current_len = 0

    for word in words:
        addition = len(word) + (1 if current else 0)
        if current and current_len + addition > max_chars:
            chunks.append(" ".join(current))
            current, current_len = _overlap_tail(current, overlap)
            addition = len(word) + (1 if current else 0)
        current.append(word)
        current_len += addition

    if current:
        chunks.append(" ".join(current))
    return chunks


def _overlap_tail(words: list[str], overlap: int) -> tuple[list[str], int]:
    tail: list[str] = []
    length = 0
    for word in reversed(words):
        addition = len(word) + (1 if tail else 0)
        if length + addition > overlap:
            break
        tail.insert(0, word)
        length += addition
    return tail, length
