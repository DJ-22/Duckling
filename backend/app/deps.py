"""Request authentication.

Access tokens are verified against Supabase's JWKS endpoint (asymmetric RS256/
ES256), never a shared HS256 secret — the rule in CLAUDE.md §4. The JWKS client
caches keys in-process, so verification adds no network round-trip after warm-up.
"""

from functools import lru_cache
import jwt
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from jwt import PyJWKClient
from pydantic import BaseModel
from .config import Settings, get_settings

_bearer = HTTPBearer(auto_error=False)


class CurrentUser(BaseModel):
    """The authenticated user, derived solely from verified JWT claims."""

    id: str  # the `sub` claim — the tenant key every row is scoped to
    email: str | None
    role: str | None


@lru_cache
def _jwk_client(jwks_url: str) -> PyJWKClient:
    return PyJWKClient(jwks_url)


def _unauthorized(detail: str) -> HTTPException:
    return HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail=detail,
        headers={"WWW-Authenticate": "Bearer"},
    )


async def get_current_user(
    credentials: HTTPAuthorizationCredentials | None = Depends(_bearer),
    settings: Settings = Depends(get_settings),
) -> CurrentUser:
    if credentials is None or not credentials.credentials:
        raise _unauthorized("Missing bearer token")

    if not settings.supabase_url:
        # Server misconfig, not a client fault — a 401 would wrongly blame the caller.
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Auth is not configured",
        )

    token = credentials.credentials

    try:
        signing_key = _jwk_client(settings.jwks_url).get_signing_key_from_jwt(token)
        claims = jwt.decode(
            token,
            signing_key.key,
            algorithms=["RS256", "ES256"],
            audience=settings.jwt_audience,
            issuer=settings.jwt_issuer,
            options={"require": ["exp", "sub"]},
        )
    except jwt.PyJWTError:
        # Never echo the verification failure reason to the client.
        raise _unauthorized("Invalid or expired token")

    sub = claims.get("sub")
    if not sub:
        raise _unauthorized("Token missing subject")

    return CurrentUser(
        id=sub,
        email=claims.get("email"),
        role=claims.get("role"),
    )
