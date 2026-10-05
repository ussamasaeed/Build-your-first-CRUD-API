from fastapi import APIRouter, Depends

from app.auth_guard import CurrentUser, require_user

router = APIRouter(tags=["access"])


@router.get("/public/info")
def public_info():
    return {"message": "Welcome stranger! This info is public."}


# Route bodies below only run after require_user has verified the token.
@router.get("/protected/profile")
def protected_profile(user: CurrentUser = Depends(require_user)):
    return {"id": user.id, "email": user.email, "created_at": user.created_at}


@router.get("/protected/dashboard")
def protected_dashboard(user: CurrentUser = Depends(require_user)):
    return {"message": f"Welcome to your dashboard, {user.email}!"}
