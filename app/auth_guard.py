"""The one guard. Add `Depends(require_user)` to any route to protect it.

All token checking lives here and nowhere else.
"""
from dataclasses import dataclass

from fastapi import Depends, Request
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from fastapi.responses import JSONResponse
from starlette.concurrency import run_in_threadpool

from app.dependencies import get_supabase


class Unauthorized(Exception):
    """Raised by the guard; turned into a 401 JSON response by the handler."""

    def __init__(self, message: str) -> None:
        self.message = message


async def unauthorized_handler(_request: Request, exc: Unauthorized) -> JSONResponse:
    return JSONResponse(status_code=401, content={"error": exc.message})


# Declares the Bearer scheme to OpenAPI, which is what puts the Authorize
# padlock in Swagger UI. auto_error=False so a missing/malformed header reaches
# our own code and produces our own {"error": ...} message instead of FastAPI's.
bearer_scheme = HTTPBearer(
    bearerFormat="JWT",
    description="Paste the `access_token` returned by POST /auth/login (no 'Bearer ' prefix).",
    auto_error=False,
)


@dataclass
class CurrentUser:
    """What the guard hands to the route: the verified user plus their token."""
    id: str
    email: str | None
    created_at: str | None
    token: str


async def require_user(
    credentials: HTTPAuthorizationCredentials | None = Depends(bearer_scheme),
    supabase=Depends(get_supabase),
) -> CurrentUser:
    token = credentials.credentials.strip() if credentials else ""
    if not token:
        raise Unauthorized("Access token required")

    # Network call to Supabase: catches expired, tampered and revoked tokens.
    try:
        result = await run_in_threadpool(supabase.auth.get_user, token)
    except Exception:
        raise Unauthorized("Invalid or expired token")

    user = getattr(result, "user", None) if result else None
    if user is None:
        raise Unauthorized("Invalid or expired token")

    created = user.created_at
    return CurrentUser(
        id=user.id,
        email=user.email,
        created_at=created.isoformat() if hasattr(created, "isoformat") else created,
        token=token,
    )
