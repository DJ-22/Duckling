from __future__ import annotations
import asyncio
from typing import Protocol
import httpx
from ..config import Settings

GEMINI_ENDPOINT = "https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent"


class ProviderError(Exception):
    pass


class RateLimited(ProviderError):
    """Raised on a 429 that survived retries, so the caller can fall through to
    the next provider."""


class AuthOrQuotaError(ProviderError):
    """A rejection that retrying cannot fix — bad key, no access to the model, or
    exhausted quota. Kept distinct from RateLimited so transient throttling and a
    hard auth/quota failure are not confused for one another."""


class LLMProvider(Protocol):
    async def complete(
        self, *, system: str, user: str, temperature: float, json_mode: bool
    ) -> str: ...


class GeminiProvider:
    def __init__(
        self,
        api_key: str,
        model: str,
        timeout: float = 60.0,
        max_attempts: int = 3,
        backoff_base: float = 2.0,
    ) -> None:
        self._api_key = api_key
        self._model = model
        self._timeout = timeout
        self._max_attempts = max_attempts
        self._backoff_base = backoff_base

    async def complete(
        self, *, system: str, user: str, temperature: float = 0.1, json_mode: bool = True
    ) -> str:
        generation: dict[str, object] = {"temperature": temperature}
        if json_mode:
            generation["responseMimeType"] = "application/json"
        body = {
            "systemInstruction": {"parts": [{"text": system}]},
            "contents": [{"role": "user", "parts": [{"text": user}]}],
            "generationConfig": generation,
        }
        url = GEMINI_ENDPOINT.format(model=self._model)

        detail = ""
        for attempt in range(self._max_attempts):
            async with httpx.AsyncClient(timeout=self._timeout) as client:
                resp = await client.post(url, params={"key": self._api_key}, json=body)

            # 400/401/403/404 are not throttling: invalid key, no access to the
            # model, or a disabled project. Retrying won't help, and a 429 rooted
            # in auth/quota must not masquerade as transient rate limiting.
            if resp.status_code in (400, 401, 403, 404):
                raise AuthOrQuotaError(
                    f"gemini rejected request ({resp.status_code}): {_api_error(resp)}"
                )

            if resp.status_code == 429:
                detail = _api_error(resp)
                if attempt < self._max_attempts - 1:
                    await asyncio.sleep(self._backoff_base * (2**attempt))
                continue

            resp.raise_for_status()
            return _extract_text(resp.json())

        raise RateLimited(
            f"gemini rate limited after {self._max_attempts} attempts: {detail}"
        )


def _api_error(resp: httpx.Response) -> str:
    """Pull Gemini's `error.status`/`error.message` out of a failed response so
    callers can tell a per-minute rate limit from a daily-quota or auth failure."""
    try:
        err = resp.json().get("error", {})
        summary = f"{err.get('status', '')}: {err.get('message', '')}".strip(": ")
        return summary or resp.text[:300]
    except (ValueError, AttributeError):
        return resp.text[:300]


def _extract_text(payload: dict) -> str:
    try:
        parts = payload["candidates"][0]["content"]["parts"]
        return "".join(part.get("text", "") for part in parts)
    except (KeyError, IndexError, TypeError) as exc:
        raise ProviderError(f"unexpected Gemini response shape: {exc}") from exc


async def complete(
    providers: list[LLMProvider],
    *,
    system: str,
    user: str,
    temperature: float = 0.1,
    json_mode: bool = True,
) -> str:
    last: Exception | None = None
    for provider in providers:
        try:
            return await provider.complete(
                system=system, user=user, temperature=temperature, json_mode=json_mode
            )
        except (RateLimited, httpx.TimeoutException) as exc:
            last = exc
    raise last or ProviderError("no providers configured")


def gemini_providers(settings: Settings) -> list[LLMProvider]:
    return [GeminiProvider(settings.gemini_api_key, settings.gemini_model)]


def grader_providers(settings: Settings) -> list[LLMProvider]:
    return gemini_providers(settings)
