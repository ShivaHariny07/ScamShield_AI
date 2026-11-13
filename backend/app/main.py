from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.errors import register_error_handlers
from app.api.v1.router import api_router
from app.core.config import settings

DESCRIPTION = (
    "**Development build — no authentication or access control.** "
    "Investigation UUIDs are resource identifiers, not credentials: anyone "
    "who obtains one can access its records. Run on localhost only. "
    "Authentication and access control are required before any public "
    "deployment (see docs/architecture/security-notes.md)."
)

app = FastAPI(title=settings.app_name, description=DESCRIPTION)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_allowed_origins,
    allow_methods=["GET", "POST"],
    allow_headers=["Content-Type"],
)
register_error_handlers(app)
app.include_router(api_router, prefix="/api/v1")


@app.get("/health", tags=["health"])
def health_check() -> dict[str, str]:
    return {"status": "ok"}
