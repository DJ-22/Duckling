from __future__ import annotations
import httpx
from ..config import Settings


class SupabaseError(Exception):
    pass


class SupabaseRest:
    """Thin PostgREST client bound to one user's access token. Every call runs as
    that user (apikey = publishable, Authorization = their JWT), so RLS — not this
    code — is the authority on which rows are visible. The backend never reads or
    writes another tenant's data even if a query is mis-scoped."""

    def __init__(self, settings: Settings, access_token: str, timeout: float = 30.0) -> None:
        self._base = settings.supabase_url.rstrip("/")
        self._timeout = timeout
        self._headers = {
            "apikey": settings.supabase_publishable_key,
            "Authorization": f"Bearer {access_token}",
            "Content-Type": "application/json",
        }

    async def _request(
        self,
        method: str,
        path: str,
        *,
        params: dict | None = None,
        json: object = None,
        prefer: str | None = None,
    ) -> object:
        headers = dict(self._headers)
        if prefer:
            headers["Prefer"] = prefer
        async with httpx.AsyncClient(base_url=self._base, timeout=self._timeout) as client:
            resp = await client.request(method, path, params=params, json=json, headers=headers)
        if resp.status_code >= 400:
            raise SupabaseError(f"{resp.status_code}: {resp.text[:300]}")
        if resp.content and resp.headers.get("content-type", "").startswith("application/json"):
            return resp.json()
        return None

    async def select(self, table: str, *, params: dict) -> list[dict]:
        return await self._request("GET", f"/rest/v1/{table}", params=params)  # type: ignore[return-value]

    async def insert(self, table: str, rows: object, *, returning: bool = True) -> list[dict] | None:
        prefer = "return=representation" if returning else "return=minimal"
        return await self._request("POST", f"/rest/v1/{table}", json=rows, prefer=prefer)  # type: ignore[return-value]

    async def update(
        self, table: str, *, params: dict, values: dict, returning: bool = True
    ) -> list[dict] | None:
        prefer = "return=representation" if returning else "return=minimal"
        return await self._request(  # type: ignore[return-value]
            "PATCH", f"/rest/v1/{table}", params=params, json=values, prefer=prefer
        )

    async def rpc(self, fn: str, payload: dict) -> object:
        return await self._request("POST", f"/rest/v1/rpc/{fn}", json=payload)


def to_pgvector(vector: list[float]) -> str:
    # pgvector's text input form; PostgREST casts this to vector(384) on insert/RPC.
    return "[" + ",".join(f"{component:.8f}" for component in vector) + "]"
