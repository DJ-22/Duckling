from __future__ import annotations
import uuid
import httpx
import pytest
from app.config import get_settings

settings = get_settings()

pytestmark = pytest.mark.skipif(
    not (
        settings.supabase_url
        and settings.supabase_secret_key
        and settings.supabase_publishable_key
    ),
    reason="Supabase env not configured (see backend/.env.example)",
)

PASSWORD = "Test-Password-123!"


def _admin_headers() -> dict[str, str]:
    key = settings.supabase_secret_key
    return {"apikey": key, "Authorization": f"Bearer {key}"}


def _user_headers(token: str) -> dict[str, str]:
    # Publishable key as apikey → PostgREST runs the request as `authenticated`;
    # the Bearer token identifies which user, so RLS resolves auth.uid().
    return {
        "apikey": settings.supabase_publishable_key,
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json",
    }


def _create_user(client: httpx.Client, email: str) -> str:
    r = client.post(
        "/auth/v1/admin/users",
        headers=_admin_headers(),
        json={"email": email, "password": PASSWORD, "email_confirm": True},
    )
    r.raise_for_status()
    return r.json()["id"]


def _delete_user(client: httpx.Client, user_id: str) -> None:
    client.request(
        "DELETE", f"/auth/v1/admin/users/{user_id}", headers=_admin_headers()
    )


def _sign_in(client: httpx.Client, email: str) -> str:
    r = client.post(
        "/auth/v1/token",
        params={"grant_type": "password"},
        headers={"apikey": settings.supabase_publishable_key},
        json={"email": email, "password": PASSWORD},
    )
    r.raise_for_status()
    return r.json()["access_token"]


def _create_subject(client: httpx.Client, token: str, user_id: str, name: str) -> str:
    r = client.post(
        "/rest/v1/subjects",
        headers={**_user_headers(token), "Prefer": "return=representation"},
        json={"user_id": user_id, "name": name},
    )
    r.raise_for_status()
    return r.json()[0]["id"]


class Tenant:
    def __init__(self, user_id: str, token: str, subject_id: str) -> None:
        self.user_id = user_id
        self.token = token
        self.subject_id = subject_id


@pytest.fixture(scope="module")
def tenants():
    """Two real users (A, B), each owning one subject. Torn down by deleting the
    users, which cascades to their rows."""
    with httpx.Client(base_url=settings.supabase_url, timeout=30) as client:
        suffix = uuid.uuid4().hex[:8]
        email_a = f"authz-a-{suffix}@example.com"
        email_b = f"authz-b-{suffix}@example.com"
        id_a = _create_user(client, email_a)
        id_b = _create_user(client, email_b)
        try:
            token_a = _sign_in(client, email_a)
            token_b = _sign_in(client, email_b)
            a = Tenant(id_a, token_a, _create_subject(client, token_a, id_a, "A subject"))
            b = Tenant(id_b, token_b, _create_subject(client, token_b, id_b, "B subject"))
            yield client, a, b
        finally:
            _delete_user(client, id_a)
            _delete_user(client, id_b)


def test_list_returns_only_own_rows(tenants):
    client, a, b = tenants
    r = client.get("/rest/v1/subjects", params={"select": "*"}, headers=_user_headers(a.token))
    r.raise_for_status()
    rows = r.json()
    ids = {row["id"] for row in rows}
    assert ids == {a.subject_id}
    assert b.subject_id not in ids


def test_cannot_read_other_tenant_row_by_id(tenants):
    client, a, b = tenants
    r = client.get(
        "/rest/v1/subjects",
        params={"id": f"eq.{b.subject_id}", "select": "*"},
        headers=_user_headers(a.token),
    )
    r.raise_for_status()
    assert r.json() == []


def test_cannot_update_other_tenant_row(tenants):
    client, a, b = tenants
    r = client.patch(
        "/rest/v1/subjects",
        params={"id": f"eq.{b.subject_id}"},
        headers={**_user_headers(a.token), "Prefer": "return=representation"},
        json={"name": "hacked by A"},
    )
    r.raise_for_status()
    assert r.json() == []  # empty result means RLS matched no row, not a silent no-op

    check = client.get(
        "/rest/v1/subjects",
        params={"id": f"eq.{b.subject_id}", "select": "name"},
        headers=_user_headers(b.token),
    )
    check.raise_for_status()
    assert check.json()[0]["name"] == "B subject"


def test_cannot_delete_other_tenant_row(tenants):
    client, a, b = tenants
    r = client.request(
        "DELETE",
        "/rest/v1/subjects",
        params={"id": f"eq.{b.subject_id}"},
        headers={**_user_headers(a.token), "Prefer": "return=representation"},
    )
    r.raise_for_status()
    assert r.json() == []

    check = client.get(
        "/rest/v1/subjects",
        params={"id": f"eq.{b.subject_id}", "select": "id"},
        headers=_user_headers(b.token),
    )
    check.raise_for_status()
    assert len(check.json()) == 1


def test_cannot_insert_row_owned_by_another_user(tenants):
    client, a, b = tenants
    r = client.post(
        "/rest/v1/subjects",
        headers={**_user_headers(a.token), "Prefer": "return=representation"},
        json={"user_id": b.user_id, "name": "spoofed"},
    )
    assert r.status_code == 403
