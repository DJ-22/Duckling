from __future__ import annotations
from fastapi import APIRouter, Depends, File, HTTPException, UploadFile, status
from ..config import get_settings
from ..db.client import SupabaseRest
from ..deps import CurrentUser, get_current_user
from ..schemas.sources import IngestResult
from ..services import ingestion
from ..services.ingest import MAX_UPLOAD_BYTES, UploadValidationError, validate_upload

router = APIRouter(prefix="/api/subjects", tags=["sources"])


async def _read_capped(file: UploadFile, cap: int) -> bytes:
    # Enforce the size cap while streaming, so an oversized upload is rejected
    # before it is fully buffered in memory.
    buffer = bytearray()
    while chunk := await file.read(1024 * 1024):
        buffer.extend(chunk)
        if len(buffer) > cap:
            raise UploadValidationError(f"file exceeds {cap} byte limit")
    return bytes(buffer)


@router.post(
    "/{subject_id}/sources",
    response_model=IngestResult,
    status_code=status.HTTP_201_CREATED,
)
async def upload_source(
    subject_id: str,
    file: UploadFile = File(...),
    user: CurrentUser = Depends(get_current_user),
) -> IngestResult:
    filename = file.filename or ""
    try:
        data = await _read_capped(file, MAX_UPLOAD_BYTES)
        validate_upload(filename, len(data))
    except UploadValidationError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc))

    db = SupabaseRest(get_settings(), user.access_token)
    try:
        return await ingestion.ingest_source(
            db, user_id=user.id, subject_id=subject_id, filename=filename, data=data
        )
    except ingestion.SubjectNotFound:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="subject not found")
