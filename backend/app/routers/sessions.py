from __future__ import annotations
from fastapi import APIRouter, Depends, HTTPException, status
from ..config import get_settings
from ..db.client import SupabaseRest
from ..deps import CurrentUser, get_current_user
from ..schemas.sessions import CompletionResult, SessionView, TurnRequest, TurnResponse
from ..services import conversation

router = APIRouter(prefix="/api", tags=["sessions"])


def _db(user: CurrentUser) -> SupabaseRest:
    return SupabaseRest(get_settings(), user.access_token)


@router.post(
    "/concepts/{concept_id}/sessions",
    response_model=SessionView,
    status_code=status.HTTP_201_CREATED,
)
async def start_session(
    concept_id: str, user: CurrentUser = Depends(get_current_user)
) -> SessionView:
    try:
        return SessionView(
            **await conversation.start_session(_db(user), user_id=user.id, concept_id=concept_id)
        )
    except conversation.ConceptNotFound:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="concept not found")


@router.get("/sessions/{session_id}", response_model=SessionView)
async def get_session(
    session_id: str, user: CurrentUser = Depends(get_current_user)
) -> SessionView:
    try:
        return SessionView(**await conversation.get_session(_db(user), session_id=session_id))
    except (conversation.SessionNotFound, conversation.ConceptNotFound):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="session not found")


@router.post("/sessions/{session_id}/turns", response_model=TurnResponse)
async def add_turn(
    session_id: str, body: TurnRequest, user: CurrentUser = Depends(get_current_user)
) -> TurnResponse:
    try:
        return TurnResponse(
            **await conversation.add_turn(
                _db(user), session_id=session_id, explanation=body.explanation
            )
        )
    except (conversation.SessionNotFound, conversation.ConceptNotFound):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="session not found")
    except conversation.SessionClosed:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT, detail="session already completed"
        )


@router.post("/sessions/{session_id}/complete", response_model=CompletionResult)
async def complete_session(
    session_id: str, user: CurrentUser = Depends(get_current_user)
) -> CompletionResult:
    try:
        return CompletionResult(
            **await conversation.complete_session(_db(user), session_id=session_id)
        )
    except conversation.SessionNotFound:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="session not found")
