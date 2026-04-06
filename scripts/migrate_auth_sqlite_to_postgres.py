import asyncio
import os
import sqlite3
from datetime import datetime, timezone
from pathlib import Path

from sqlalchemy import select

from app.models.auth import User
from app.services.auth_db import init_auth_db
from db.database import AsyncSessionLocal


DEFAULT_SQLITE_PATH = Path(__file__).resolve().parents[1] / "culture_sim.db"


def parse_timestamp(value: str | None) -> datetime | None:
    if not value:
        return None
    parsed = datetime.fromisoformat(value)
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=timezone.utc)
    return parsed


def read_sqlite_users(sqlite_path: Path) -> list[dict]:
    conn = sqlite3.connect(sqlite_path)
    conn.row_factory = sqlite3.Row
    try:
        rows = conn.execute(
            """
            SELECT
                email,
                password_hash,
                password_salt,
                approved,
                is_employee,
                is_management,
                is_admin,
                created_at,
                last_login_at
            FROM users
            ORDER BY id ASC
            """
        ).fetchall()
        return [dict(row) for row in rows]
    finally:
        conn.close()


async def migrate_users(sqlite_path: Path) -> None:
    if not sqlite_path.exists():
        raise FileNotFoundError(f"SQLite database not found: {sqlite_path}")

    await init_auth_db()
    sqlite_users = read_sqlite_users(sqlite_path)

    async with AsyncSessionLocal() as session:
        for row in sqlite_users:
            existing = await session.execute(select(User).where(User.email == row["email"]))
            if existing.scalar_one_or_none() is not None:
                continue

            session.add(
                User(
                    email=row["email"],
                    password_hash=row["password_hash"],
                    password_salt=row["password_salt"],
                    approved=bool(row["approved"]),
                    is_employee=bool(row["is_employee"]),
                    is_management=bool(row["is_management"]),
                    is_admin=bool(row["is_admin"]),
                    created_at=parse_timestamp(row["created_at"]),
                    last_login_at=parse_timestamp(row["last_login_at"]),
                )
            )

        await session.commit()


if __name__ == "__main__":
    sqlite_path = Path(
        os.getenv("SQLITE_AUTH_DB_PATH", str(DEFAULT_SQLITE_PATH))
    ).expanduser()
    asyncio.run(migrate_users(sqlite_path))
