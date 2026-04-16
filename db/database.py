import os
from pathlib import Path
from typing import AsyncIterator
from urllib.parse import parse_qsl, urlencode, urlsplit, urlunsplit

from dotenv import load_dotenv
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.orm import DeclarativeBase

load_dotenv()

DEFAULT_SQLITE_PATH = Path(__file__).resolve().parents[1] / "culture_sim.db"


def normalize_database_url(url: str) -> str:
    normalized = url.strip()
    if normalized.startswith("sqlite:///") or normalized.startswith("sqlite+aiosqlite:///"):
        return normalized.replace("sqlite:///", "sqlite+aiosqlite:///", 1)

    if normalized.startswith("postgres://"):
        normalized = normalized.replace("postgres://", "postgresql+asyncpg://", 1)
    elif normalized.startswith("postgresql://"):
        normalized = normalized.replace("postgresql://", "postgresql+asyncpg://", 1)

    parts = urlsplit(normalized)
    query = dict(parse_qsl(parts.query, keep_blank_values=True))
    sslmode = query.pop("sslmode", "").lower()
    if sslmode == "require":
        query["ssl"] = "require"

    normalized = urlunsplit(
        (
            parts.scheme,
            parts.netloc,
            parts.path,
            urlencode(query),
            parts.fragment,
        )
    )
    return normalized


raw_database_url = os.getenv("DATABASE_URL", "").strip()
if raw_database_url:
    DATABASE_URL = normalize_database_url(raw_database_url)
else:
    DATABASE_URL = f"sqlite+aiosqlite:///{DEFAULT_SQLITE_PATH.as_posix()}"


class Base(DeclarativeBase):
    pass


engine = create_async_engine(
    DATABASE_URL,
    echo=False,
    pool_pre_ping=True,
)
AsyncSessionLocal = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)


async def get_db_session() -> AsyncIterator[AsyncSession]:
    async with AsyncSessionLocal() as session:
        yield session


async def check_db_connection() -> None:
    async with engine.connect() as connection:
        await connection.execute(text("SELECT 1"))
