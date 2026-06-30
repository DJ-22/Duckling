from __future__ import annotations
import asyncio
import uuid
import httpx
import pytest
from app.config import get_settings
from app.db import repo
from app.db.client import SupabaseRest
from app.services import conversation, dashboard, ingestion

settings = get_settings()

pytestmark = pytest.mark.skipif(
    not (
        settings.supabase_url
        and settings.supabase_secret_key
        and settings.supabase_publishable_key
        and settings.gemini_api_key
    ),
    reason="Supabase + Gemini env not configured (see backend/.env.example)",
)

PASSWORD = "Test-Password-123!"
SOURCE = (
    "Photosynthesis is how green plants make food. Chlorophyll in the leaves absorbs "
    "light energy. That energy splits water and, with carbon dioxide, builds glucose. "
    "Oxygen is released as a by-product."
).encode()
EXPLANATION = (
    "Chlorophyll absorbs light energy, which splits water and combines carbon dioxide "
    "into glucose that stores the energy, releasing oxygen as a by-product."
)


def _admin_headers() -> dict[str, str]:
    key = settings.supabase_secret_key
    return {"apikey": key, "Authorization": f"Bearer {key}"}


@pytest.fixture(scope="module")
def world():
    with httpx.Client(base_url=settings.supabase_url, timeout=30) as client:
        email = f"dash-{uuid.uuid4().hex[:8]}@example.com"
        created = client.post(
            "/auth/v1/admin/users",
            headers=_admin_headers(),
            json={"email": email, "password": PASSWORD, "email_confirm": True},
        )
        created.raise_for_status()
        user_id = created.json()["id"]
        try:
            signed_in = client.post(
                "/auth/v1/token",
                params={"grant_type": "password"},
                headers={"apikey": settings.supabase_publishable_key},
                json={"email": email, "password": PASSWORD},
            )
            signed_in.raise_for_status()
            db = SupabaseRest(settings, signed_in.json()["access_token"])

            async def run():
                subject = await repo.create_subject(db, user_id=user_id, name="Biology")
                subject_id = subject["id"]
                await ingestion.ingest_source(
                    db, user_id=user_id, subject_id=subject_id,
                    filename="photo.txt", data=SOURCE,
                )
                concept_id = (await repo.list_concepts(db, subject_id))[0]["id"]

                started = await conversation.start_session(
                    db, user_id=user_id, concept_id=concept_id, felt=40
                )
                await conversation.add_turn(db, session_id=started["id"], explanation=EXPLANATION)
                await conversation.complete_session(
                    db, session_id=started["id"], user_id=user_id
                )

                return {
                    "concept_id": concept_id,
                    "subject_id": subject_id,
                    "mastery": await repo.get_mastery(db, concept_id),
                    "board": await dashboard.get_dashboard(db, user_id=user_id),
                    "concepts": await repo.list_concepts(db, subject_id),
                }

            yield asyncio.run(run())
        finally:
            client.request(
                "DELETE", f"/auth/v1/admin/users/{user_id}", headers=_admin_headers()
            )


def test_completion_writes_mastery(world):
    mastery = world["mastery"]
    assert mastery is not None
    assert 0 <= mastery["comprehension"] <= 100
    assert mastery["ease"] >= 1.3


def test_dashboard_lists_subject_and_mastery(world):
    board = world["board"]
    assert any(s["name"] == "Biology" for s in board["subjects"])
    assert any(m["concept_id"] == world["concept_id"] for m in board["mastery"])


def test_dashboard_has_no_open_session_after_completion(world):
    assert world["board"]["in_progress"] == []


def test_streak_is_one_after_practicing_today(world):
    assert world["board"]["streak"] == 1


def test_concepts_are_listable_for_a_subject(world):
    assert world["concepts"]
    assert all({"id", "name"} <= set(c) for c in world["concepts"])
