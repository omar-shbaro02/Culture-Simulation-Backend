from typing import Annotated

from fastapi import APIRouter, Depends, Header, HTTPException, status
from pydantic import BaseModel, Field
import sqlite3

from app.services.auth_db import (
    create_session,
    create_user,
    delete_session,
    get_user_by_session,
    init_auth_db,
    list_users,
    update_user_access,
    verify_user_credentials,
)

router = APIRouter(prefix="/auth", tags=["Auth"])


class AuthCredentials(BaseModel):
    email: str
    password: str = Field(min_length=8, max_length=128)


def _validate_email(email: str) -> str:
    normalized = email.strip().lower()
    if "@" not in normalized or "." not in normalized.split("@")[-1]:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Enter a valid email address.",
        )
    return normalized


class ApprovalUpdate(BaseModel):
    approved: bool
    is_employee: bool = False
    is_management: bool = False


def _extract_token(authorization: str | None) -> str:
    if not authorization:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication required.",
        )
    scheme, _, token = authorization.partition(" ")
    if scheme.lower() != "bearer" or not token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid authentication token.",
        )
    return token


def require_auth(
    authorization: Annotated[str | None, Header()] = None,
):
    token = _extract_token(authorization)
    user = get_user_by_session(token)
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Session expired or invalid.",
        )
    return user


def require_admin(user=Depends(require_auth)):
    if not user.get("is_admin"):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin access required.",
        )
    return user


def require_employee(user=Depends(require_auth)):
    if not user.get("approved") or not user.get("is_employee"):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Employee access required.",
        )
    return user


def require_management(user=Depends(require_auth)):
    if not user.get("approved") or not (user.get("is_management") or user.get("is_admin")):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Management access required.",
        )
    return user


@router.post("/signup")
async def signup(payload: AuthCredentials):
    init_auth_db()
    try:
        user = create_user(_validate_email(payload.email), payload.password)
    except sqlite3.IntegrityError:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="An account with this email already exists.",
        )

    return {
        "user": user,
        "message": (
            "Account created and approved."
            if user.get("approved")
            else "Account created. Approval is pending."
        ),
    }


@router.post("/login")
async def login(payload: AuthCredentials):
    user = verify_user_credentials(_validate_email(payload.email), payload.password)
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password.",
        )
    if not user.get("approved"):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Your account is awaiting approval.",
        )
    if not user.get("is_employee") and not user.get("is_management") and not user.get("is_admin"):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Your account does not have an assigned access role yet.",
        )

    token = create_session(int(user["id"]))
    refreshed_user = get_user_by_session(token) or user
    return {"token": token, "user": refreshed_user}


@router.get("/me")
async def me(user=Depends(require_auth)):
    return {"user": user}


@router.post("/logout")
async def logout(
    authorization: Annotated[str | None, Header()] = None,
    _user=Depends(require_auth),
):
    token = _extract_token(authorization)
    delete_session(token)
    return {"ok": True}


@router.get("/users")
async def users(_admin=Depends(require_admin)):
    return {"users": list_users()}


@router.patch("/users/{user_id}/approval")
async def set_approval(user_id: int, payload: ApprovalUpdate, _admin=Depends(require_admin)):
    user = update_user_access(
        user_id,
        payload.approved,
        payload.is_employee,
        payload.is_management,
    )
    if user is None:
        raise HTTPException(status_code=404, detail="User not found.")
    return {"user": user}
