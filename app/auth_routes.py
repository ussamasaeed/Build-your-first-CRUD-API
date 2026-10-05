from typing import Any, Tuple

from fastapi import APIRouter, Depends, Request, Response, status
from fastapi.encoders import jsonable_encoder
from fastapi.responses import JSONResponse
from starlette.concurrency import run_in_threadpool
from supabase_auth.errors import AuthApiError, AuthError

from app.auth_guard import CurrentUser, require_user
from app.dependencies import get_supabase

router = APIRouter(prefix="/auth", tags=["auth"])


def _error(code: int, message: str) -> JSONResponse:
    return JSONResponse(status_code=code, content={"error": message})


async def _read_credentials(request: Request) -> Tuple[str | None, str | None, JSONResponse | None]:
    """Server never trusts the client: parse defensively, validate, trim.

    Returns (email, password, error_response). If error_response is set, return it.
    """
    try:
        body: Any = await request.json()
    except Exception:
        return None, None, _error(status.HTTP_400_BAD_REQUEST, "Request body must be valid JSON")

    if not isinstance(body, dict):
        return None, None, _error(status.HTTP_400_BAD_REQUEST, "Request body must be a JSON object")

    email = body.get("email")
    password = body.get("password")

    if not isinstance(email, str) or not email.strip():
        return None, None, _error(status.HTTP_400_BAD_REQUEST, "Email is required")
    if not isinstance(password, str) or not password:
        return None, None, _error(status.HTTP_400_BAD_REQUEST, "Password is required")

    return email.strip(), password, None


@router.post("/signup", status_code=status.HTTP_201_CREATED)
async def signup(request: Request, supabase=Depends(get_supabase)):
    email, password, err = await _read_credentials(request)
    if err:
        return err

    try:
        result = await run_in_threadpool(
            supabase.auth.sign_up, {"email": email, "password": password}
        )
    except AuthApiError as exc:
        # e.g. weak password, invalid email, already registered
        return _error(status.HTTP_400_BAD_REQUEST, exc.message)
    except AuthError as exc:
        return _error(status.HTTP_400_BAD_REQUEST, str(exc))

    if result.user is None:
        return _error(status.HTTP_400_BAD_REQUEST, "Sign up failed")

    return JSONResponse(
        status_code=status.HTTP_201_CREATED,
        content=jsonable_encoder(result.user.model_dump(mode="json")),
    )


@router.post("/login")
async def login(request: Request, supabase=Depends(get_supabase)):
    email, password, err = await _read_credentials(request)
    if err:
        return err

    try:
        result = await run_in_threadpool(
            supabase.auth.sign_in_with_password, {"email": email, "password": password}
        )
    except AuthError:
        # Same message for wrong password / unknown user / unconfirmed email:
        # never tell an attacker which part was wrong.
        return _error(status.HTTP_401_UNAUTHORIZED, "Invalid login credentials")

    session = result.session
    if session is None:
        return _error(status.HTTP_401_UNAUTHORIZED, "Invalid login credentials")

    return {
        "access_token": session.access_token,
        "refresh_token": session.refresh_token,
    }


@router.post("/logout", status_code=status.HTTP_204_NO_CONTENT)
async def logout(
    user: CurrentUser = Depends(require_user),
    supabase=Depends(get_supabase),
):
    # Protected by the same guard. A stateless API has no stored session for
    # client.auth.sign_out() to read, so we use the SDK's server-side form,
    # which signs out using the caller's own access token.
    try:
        await run_in_threadpool(supabase.auth.admin.sign_out, user.token)
    except AuthError:
        pass  # token already revoked/expired between guard and here: still logged out
    return Response(status_code=status.HTTP_204_NO_CONTENT)
