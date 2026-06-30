from __future__ import annotations
from fastapi import APIRouter, Depends
from ..config import get_settings
from ..db.client import SupabaseRest
from ..deps import CurrentUser, get_current_user
from ..schemas.dashboard import Dashboard
from ..services import dashboard

router = APIRouter(prefix="/api", tags=["dashboard"])


@router.get("/dashboard", response_model=Dashboard)
async def get_dashboard(user: CurrentUser = Depends(get_current_user)) -> Dashboard:
    db = SupabaseRest(get_settings(), user.access_token)
    return Dashboard(**await dashboard.get_dashboard(db, user_id=user.id))
