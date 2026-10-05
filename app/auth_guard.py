"""The one guard. Add `Depends(require_user)` to any route to protect it.

All token checking lives here and nowhere else.
"""
from dataclasses import dataclass

from fastapi import Depends, Header, Request
from fastapi.responses import JSONResponse
from starlette.concurrency import run_in_threadpool

from app.dependencies import get_supabase


class Unauthorized(Exception):
    """Raised by the guard; turned into a 401 JSON response by the handler."""

    def __init__(self, message: str) -> None:
        self.message = message


async def unauthorized_handler(_request: Request, exc: Unauthorized) -> JSONResponse:
    return JSONResponse(status_code=401, content={"error": exc.message})


def _extract_bearer_token(authorization: str | None) -> str | None:
    """Token from 'Authorization: Bearer <token>', or None if missing/malformed."""
    if not authorization:
        return None
    parts = authorization.strip().split()
    if len(parts) != 2 or parts[0].lower() != "bearer":
        return None
    return parts[1]


@dataclass
class CurrentUser:
    """What the guard hands to the route: the verified user plus their token."""
    id: str
    email: str | None
    created_at: str | None
    token: str


async def require_user(
    authorization: str | None = Header(default=None),
    supabase=Depends(get_supabase),
) -> CurrentUser:
    token = _extract_bearer_token(authorization)
    if token is None:
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
