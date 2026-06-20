from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from .config import get_settings
from .routers import auth, sources

settings = get_settings()

app = FastAPI(title="Duckling API", version="0.1.0")

# Locked to the single frontend origin, never "*".
app.add_middleware(
    CORSMiddleware,
    allow_origins=[settings.frontend_origin],
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"],
    allow_headers=["Authorization", "Content-Type"],
)

app.include_router(auth.router)
app.include_router(sources.router)


@app.get("/health", tags=["meta"])
async def health() -> dict[str, str]:
    """Liveness probe — no auth, safe for an external uptime monitor to poll."""
    return {"status": "ok"}
