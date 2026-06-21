from __future__ import annotations
import asyncio
import uuid
import httpx
import pytest
from app.config import get_settings
from app.db.client import SupabaseRest
from app.services import conversation, ingestion

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
    "Photosynthesis is how green plants make food. Chlorophyll in the leaves "
    "absorbs light energy. That energy splits water and, with carbon dioxide from "
    "the air, builds glucose. Oxygen is released as a by-product. The glucose "
    "stores the captured energy for the plant to use later."
).encode()

VAGUE = "Photosynthesis is how plants make their food from sunlight. It's important for life on Earth."
FULLER = (
    "Chlorophyll in the leaves absorbs light energy, and that energy splits water "
    "and combines carbon dioxide into glucose, which stores the energy, releasing "
    "oxygen as a by-product."
)


def _admin_headers() -> dict[str, str]:
    key = settings.supabase_secret_key
    return {"apikey": key, "Authorization": f"Bearer {key}"}


@pytest.fixture(scope="module")
def flow():
    with httpx.Client(base_url=settings.supabase_url, timeout=30) as client:
        email = f"loop-{uuid.uuid4().hex[:8]}@example.com"
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
            token = signed_in.json()["access_token"]
            subject = client.post(
                "/rest/v1/subjects",
                headers={
                    "apikey": settings.supabase_publishable_key,
                    "Authorization": f"Bearer {token}",
                    "Content-Type": "application/json",
                    "Prefer": "return=representation",
                },
                json={"user_id": user_id, "name": "Biology"},
            )
            subject.raise_for_status()
            subject_id = subject.json()[0]["id"]
            db = SupabaseRest(settings, token)

            async def run():
                await ingestion.ingest_source(
                    db, user_id=user_id, subject_id=subject_id,
                    filename="photo.txt", data=SOURCE,
                )
                concepts = await db.select(
                    "concepts",
                    params={"subject_id": f"eq.{subject_id}", "select": "id", "limit": "1"},
                )
                concept_id = concepts[0]["id"]

                started = await conversation.start_session(
                    db, user_id=user_id, concept_id=concept_id
                )
                turn1 = await conversation.add_turn(db, session_id=started["id"], explanation=VAGUE)
                after1 = await conversation.get_session(db, session_id=started["id"])
                turn2 = await conversation.add_turn(db, session_id=started["id"], explanation=FULLER)
                resumed = await conversation.get_session(db, session_id=started["id"])
                completed = await conversation.complete_session(db, session_id=started["id"])
                return {
                    "started": started,
                    "turn1": turn1,
                    "after1": after1,
                    "turn2": turn2,
                    "resumed": resumed,
                    "completed": completed,
                }

            yield asyncio.run(run())
        finally:
            client.request(
                "DELETE", f"/auth/v1/admin/users/{user_id}", headers=_admin_headers()
            )


def test_session_starts_in_progress_and_empty(flow):
    assert flow["started"]["status"] == "in_progress"
    assert flow["started"]["transcript"] == []
    assert flow["started"]["comprehension"] == 0


def test_first_turn_returns_a_probing_question(flow):
    turn1 = flow["turn1"]
    assert turn1["turn_index"] == 0
    assert turn1["question"].strip()


def test_turn_is_written_through_immediately(flow):
    # A fresh read after one turn rehydrates that turn — the write-through resume path.
    transcript = flow["after1"]["transcript"]
    assert len(transcript) == 1
    assert set(transcript[0]) >= {"user", "grade", "student"}


def test_fuller_explanation_does_not_lower_comprehension(flow):
    assert flow["turn2"]["comprehension"] >= flow["turn1"]["comprehension"]


def test_resume_rehydrates_full_conversation(flow):
    assert len(flow["resumed"]["transcript"]) == 2
    assert flow["resumed"]["status"] == "in_progress"


def test_completion_closes_session(flow):
    assert flow["completed"]["final_overall"] == pytest.approx(
        flow["completed"]["final_overall"]
    )
    assert 0 <= flow["completed"]["comprehension"] <= 100
