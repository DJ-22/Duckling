from __future__ import annotations
import asyncio
import uuid
import httpx
import pytest
from app.config import get_settings
from app.db.client import SupabaseRest
from app.services import ingestion, retrieval

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

SOURCE_TEXT = (
    "Photosynthesis is how green plants make food. Chlorophyll in the leaves "
    "absorbs light energy. That energy splits water and, with carbon dioxide from "
    "the air, builds glucose. Oxygen is released as a by-product. The glucose "
    "stores the captured energy for the plant to use later."
).encode()


def _admin_headers() -> dict[str, str]:
    key = settings.supabase_secret_key
    return {"apikey": key, "Authorization": f"Bearer {key}"}


@pytest.fixture(scope="module")
def tenant():
    with httpx.Client(base_url=settings.supabase_url, timeout=30) as client:
        email = f"ingest-{uuid.uuid4().hex[:8]}@example.com"
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
            yield {
                "db": SupabaseRest(settings, token),
                "user_id": user_id,
                "subject_id": subject.json()[0]["id"],
            }
        finally:
            client.request(
                "DELETE", f"/auth/v1/admin/users/{user_id}", headers=_admin_headers()
            )


@pytest.fixture(scope="module")
def ingested(tenant):
    result = asyncio.run(
        ingestion.ingest_source(
            tenant["db"],
            user_id=tenant["user_id"],
            subject_id=tenant["subject_id"],
            filename="photosynthesis.txt",
            data=SOURCE_TEXT,
        )
    )
    return tenant, result


def test_ingest_stores_chunks_and_concepts(ingested):
    _, result = ingested
    assert result.cached is False
    assert result.chunks >= 1
    assert result.concepts >= 1


def test_retrieval_is_scoped_and_relevant(ingested):
    tenant, _ = ingested
    rows = asyncio.run(
        retrieval.retrieve(
            tenant["db"],
            subject_id=tenant["subject_id"],
            query="how do plants turn sunlight into food?",
            k=3,
        )
    )
    assert rows
    joined = " ".join(row["content"] for row in rows).lower()
    assert "chlorophyll" in joined or "glucose" in joined


def test_reingesting_same_bytes_is_cached(ingested):
    tenant, _ = ingested
    again = asyncio.run(
        ingestion.ingest_source(
            tenant["db"],
            user_id=tenant["user_id"],
            subject_id=tenant["subject_id"],
            filename="photosynthesis.txt",
            data=SOURCE_TEXT,
        )
    )
    assert again.cached is True
    assert again.chunks == 0
    assert again.concepts == 0


def test_subject_ownership_is_enforced(tenant):
    with pytest.raises(ingestion.SubjectNotFound):
        asyncio.run(
            ingestion.ingest_source(
                tenant["db"],
                user_id=tenant["user_id"],
                subject_id=str(uuid.uuid4()),  # a subject the user does not own
                filename="x.txt",
                data=b"unrelated",
            )
        )
