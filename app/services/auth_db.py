import hashlib
import os
import secrets
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List, Optional
from uuid import uuid4

from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.auth import Session, User
from db.database import Base, engine

SESSION_DURATION_DAYS = 30


def _utc_now() -> datetime:
    return datetime.now(timezone.utc)


def _to_iso(value: datetime | None) -> str | None:
    if value is None:
        return None
    if value.tzinfo is None:
        value = value.replace(tzinfo=timezone.utc)
    return value.isoformat()


def _user_to_dict(user: User | None) -> Optional[Dict[str, Any]]:
    if user is None:
        return None
    return {
        "id": user.id,
        "email": user.email,
        "approved": bool(user.approved),
        "is_employee": bool(user.is_employee),
        "is_management": bool(user.is_management),
        "is_admin": bool(user.is_admin),
        "created_at": _to_iso(user.created_at),
        "last_login_at": _to_iso(user.last_login_at),
    }


async def init_auth_db() -> None:
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)


def _hash_password(password: str, salt_hex: str) -> str:
    return hashlib.pbkdf2_hmac(
        "sha256",
        password.encode("utf-8"),
        bytes.fromhex(salt_hex),
        100_000,
    ).hex()


async def create_user(session: AsyncSession, email: str, password: str) -> Dict[str, Any]:
    normalized_email = email.strip().lower()
    salt_hex = os.urandom(16).hex()
    password_hash = _hash_password(password, salt_hex)
    created_at = _utc_now()

    result = await session.execute(select(func.count()).select_from(User))
    existing_count = int(result.scalar_one())
    is_first_user = existing_count == 0

    user = User(
        email=normalized_email,
        password_hash=password_hash,
        password_salt=salt_hex,
        approved=is_first_user,
        is_employee=False,
        is_management=is_first_user,
        is_admin=is_first_user,
        created_at=created_at,
    )
    session.add(user)

    try:
        await session.commit()
    except IntegrityError:
        await session.rollback()
        raise

    await session.refresh(user)
    return _user_to_dict(user) or {}


async def _get_user_by_email(session: AsyncSession, email: str) -> User | None:
    normalized_email = email.strip().lower()
    result = await session.execute(select(User).where(User.email == normalized_email))
    return result.scalar_one_or_none()


async def verify_user_credentials(
    session: AsyncSession, email: str, password: str
) -> Optional[Dict[str, Any]]:
    user = await _get_user_by_email(session, email)
    if user is None:
        return None

    expected_hash = _hash_password(password, user.password_salt)
    if not secrets.compare_digest(expected_hash, user.password_hash):
        return None

    return _user_to_dict(user)


async def create_session(session: AsyncSession, user_id: int) -> str:
    token = uuid4().hex
    created_at = _utc_now()
    expires_at = created_at + timedelta(days=SESSION_DURATION_DAYS)

    auth_session = Session(
        token=token,
        user_id=user_id,
        created_at=created_at,
        expires_at=expires_at,
    )
    session.add(auth_session)

    user = await session.get(User, user_id)
    if user is not None:
        user.last_login_at = created_at

    await session.commit()
    return token


async def get_user_by_session(session: AsyncSession, token: str) -> Optional[Dict[str, Any]]:
    result = await session.execute(select(Session).where(Session.token == token))
    auth_session = result.scalar_one_or_none()
    if auth_session is None:
        return None

    expires_at = auth_session.expires_at
    if expires_at.tzinfo is None:
        expires_at = expires_at.replace(tzinfo=timezone.utc)

    if expires_at <= _utc_now():
        await session.delete(auth_session)
        await session.commit()
        return None

    user = await session.get(User, auth_session.user_id)
    return _user_to_dict(user)


async def delete_session(session: AsyncSession, token: str) -> None:
    result = await session.execute(select(Session).where(Session.token == token))
    auth_session = result.scalar_one_or_none()
    if auth_session is None:
        return

    await session.delete(auth_session)
    await session.commit()


async def list_users(session: AsyncSession) -> List[Dict[str, Any]]:
    result = await session.execute(select(User).order_by(User.approved.asc(), User.created_at.desc()))
    users = result.scalars().all()
    return [_user_to_dict(user) for user in users if user is not None]


async def update_user_access(
    session: AsyncSession,
    user_id: int,
    approved: bool,
    is_employee: bool,
    is_management: bool,
) -> Optional[Dict[str, Any]]:
    user = await session.get(User, user_id)
    if user is None:
        return None

    user.approved = approved
    user.is_employee = is_employee
    user.is_management = is_management
    await session.commit()
    await session.refresh(user)
    return _user_to_dict(user)
