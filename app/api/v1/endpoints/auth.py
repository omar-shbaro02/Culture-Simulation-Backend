from typing import Annotated

from fastapi import APIRouter, Depends, Header, HTTPException, status
from pydantic import BaseModel, Field
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.services.auth_db import (
    create_session,
    create_user,
    delete_session,
    get_user_by_session,
    list_users,
    update_user_access,
    verify_user_credentials,
)
from app.services.email_service import send_signup_notification
from db.database import get_db_session

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


async def require_auth(
    authorization: Annotated[str | None, Header()] = None,
    db: AsyncSession = Depends(get_db_session),
):
    token = _extract_token(authorization)
    user = await get_user_by_session(db, token)
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
async def signup(payload: AuthCredentials, db: AsyncSession = Depends(get_db_session)):
    try:
        user = await create_user(db, _validate_email(payload.email), payload.password)
    except IntegrityError:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="An account with this email already exists.",
        )

    await send_signup_notification(user["email"], bool(user.get("approved")))

    return {
        "user": user,
        "message": (
            "Account created and approved."
            if user.get("approved")
            else "Account created. Approval is pending."
        ),
    }


@router.post("/login")
async def login(payload: AuthCredentials, db: AsyncSession = Depends(get_db_session)):
    user = await verify_user_credentials(db, _validate_email(payload.email), payload.password)
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

    token = await create_session(db, int(user["id"]))
    refreshed_user = await get_user_by_session(db, token) or user
    return {"token": token, "user": refreshed_user}


@router.get("/me")
async def me(user=Depends(require_auth)):
    return {"user": user}


@router.post("/logout")
async def logout(
    authorization: Annotated[str | None, Header()] = None,
    _user=Depends(require_auth),
    db: AsyncSession = Depends(get_db_session),
):
    token = _extract_token(authorization)
    await delete_session(db, token)
    return {"ok": True}


@router.get("/users")
async def users(_admin=Depends(require_admin), db: AsyncSession = Depends(get_db_session)):
    return {"users": await list_users(db)}


@router.patch("/users/{user_id}/approval")
async def set_approval(
    user_id: int,
    payload: ApprovalUpdate,
    _admin=Depends(require_admin),
    db: AsyncSession = Depends(get_db_session),
):
    user = await update_user_access(
        db,
        user_id,
        payload.approved,
        payload.is_employee,
        payload.is_management,
    )
    if user is None:
        raise HTTPException(status_code=404, detail="User not found.")
    return {"user": user}
