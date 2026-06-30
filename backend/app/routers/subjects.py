from __future__ import annotations
from fastapi import APIRouter, Depends, HTTPException, status
from ..config import get_settings
from ..db import repo
from ..db.client import SupabaseRest
from ..deps import CurrentUser, get_current_user
from ..schemas.subjects import ConceptInfo, CreateSubjectRequest, SubjectInfo

router = APIRouter(prefix="/api/subjects", tags=["subjects"])


def _db(user: CurrentUser) -> SupabaseRest:
    return SupabaseRest(get_settings(), user.access_token)


@router.post("", response_model=SubjectInfo, status_code=status.HTTP_201_CREATED)
async def create_subject(
    body: CreateSubjectRequest, user: CurrentUser = Depends(get_current_user)
) -> SubjectInfo:
    row = await repo.create_subject(_db(user), user_id=user.id, name=body.name)
    return SubjectInfo(**row)


@router.get("/{subject_id}/concepts", response_model=list[ConceptInfo])
async def list_concepts(
    subject_id: str, user: CurrentUser = Depends(get_current_user)
) -> list[ConceptInfo]:
    db = _db(user)
    if await repo.get_owned_subject(db, subject_id) is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="subject not found")
    return [ConceptInfo(**row) for row in await repo.list_concepts(db, subject_id)]
