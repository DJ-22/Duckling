from fastapi import APIRouter, Depends
from pydantic import BaseModel
from ..deps import CurrentUser, get_current_user

router = APIRouter(prefix="/api", tags=["auth"])


class MeResponse(BaseModel):
    id: str
    email: str | None
    role: str | None


@router.get("/me", response_model=MeResponse)
async def read_me(user: CurrentUser = Depends(get_current_user)) -> MeResponse:
    """Return the authenticated user, derived only from verified JWT claims."""
    return MeResponse(id=user.id, email=user.email, role=user.role)
