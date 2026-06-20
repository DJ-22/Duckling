from functools import lru_cache
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    supabase_url: str = ""
    # Bypasses RLS — backend-only, never sent to the client.
    supabase_secret_key: str = ""
    # Public by design (protected by RLS). Used as the PostgREST apikey in the
    # tenant-isolation tests so requests run as the `authenticated` role.
    supabase_publishable_key: str = ""
    frontend_origin: str = "http://localhost:5173"
    jwt_audience: str = "authenticated"

    gemini_api_key: str = ""
    gemini_model: str = "gemini-2.5-flash"

    @property
    def jwks_url(self) -> str:
        """Supabase publishes signing keys here for asymmetric (RS256/ES256) JWTs."""
        return f"{self.supabase_url.rstrip('/')}/auth/v1/.well-known/jwks.json"

    @property
    def jwt_issuer(self) -> str:
        """Issuer claim Supabase stamps on access tokens."""
        return f"{self.supabase_url.rstrip('/')}/auth/v1"


@lru_cache
def get_settings() -> Settings:
    return Settings()
