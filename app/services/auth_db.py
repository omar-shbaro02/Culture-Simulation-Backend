import hashlib
import os
import secrets
import sqlite3
from contextlib import contextmanager
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Dict, Iterator, List, Optional
from uuid import uuid4

DEFAULT_DB_PATH = Path(__file__).resolve().parents[2] / "culture_sim.db"
DB_PATH = Path(os.getenv("AUTH_DB_PATH", str(DEFAULT_DB_PATH))).expanduser()
SESSION_DURATION_DAYS = 30


def _utc_now() -> datetime:
    return datetime.now(timezone.utc)


def _utc_now_iso() -> str:
    return _utc_now().isoformat()


def _row_to_user(row: sqlite3.Row | None) -> Optional[Dict[str, Any]]:
    if row is None:
        return None
    return {
        "id": row["id"],
        "email": row["email"],
        "approved": bool(row["approved"]),
        "is_employee": bool(row["is_employee"]),
        "is_management": bool(row["is_management"]),
        "is_admin": bool(row["is_admin"]),
        "created_at": row["created_at"],
        "last_login_at": row["last_login_at"],
    }


@contextmanager
def get_connection() -> Iterator[sqlite3.Connection]:
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    try:
        yield conn
        conn.commit()
    finally:
        conn.close()


def init_auth_db() -> None:
    with get_connection() as conn:
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                email TEXT NOT NULL UNIQUE,
                password_hash TEXT NOT NULL,
                password_salt TEXT NOT NULL,
                approved INTEGER NOT NULL DEFAULT 0,
                is_employee INTEGER NOT NULL DEFAULT 0,
                is_management INTEGER NOT NULL DEFAULT 0,
                is_admin INTEGER NOT NULL DEFAULT 0,
                created_at TEXT NOT NULL,
                last_login_at TEXT
            )
            """
        )
        columns = {
            row["name"]
            for row in conn.execute("PRAGMA table_info(users)").fetchall()
        }
        if "is_employee" not in columns:
            conn.execute(
                "ALTER TABLE users ADD COLUMN is_employee INTEGER NOT NULL DEFAULT 0"
            )
        if "is_management" not in columns:
            conn.execute(
                "ALTER TABLE users ADD COLUMN is_management INTEGER NOT NULL DEFAULT 0"
            )
        conn.execute(
            """
            UPDATE users
            SET is_management = 1
            WHERE is_admin = 1 AND is_management = 0
            """
        )
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS sessions (
                token TEXT PRIMARY KEY,
                user_id INTEGER NOT NULL,
                created_at TEXT NOT NULL,
                expires_at TEXT NOT NULL,
                FOREIGN KEY(user_id) REFERENCES users(id) ON DELETE CASCADE
            )
            """
        )
        conn.execute(
            "CREATE INDEX IF NOT EXISTS idx_sessions_user_id ON sessions(user_id)"
        )


def _hash_password(password: str, salt_hex: str) -> str:
    return hashlib.pbkdf2_hmac(
        "sha256",
        password.encode("utf-8"),
        bytes.fromhex(salt_hex),
        100_000,
    ).hex()


def create_user(email: str, password: str) -> Dict[str, Any]:
    normalized_email = email.strip().lower()
    salt_hex = os.urandom(16).hex()
    password_hash = _hash_password(password, salt_hex)
    created_at = _utc_now_iso()

    with get_connection() as conn:
        existing_count = conn.execute("SELECT COUNT(*) AS count FROM users").fetchone()[
            "count"
        ]
        is_first_user = int(existing_count) == 0
        approved = 1 if is_first_user else 0
        is_admin = 1 if is_first_user else 0
        is_management = 1 if is_first_user else 0
        is_employee = 0

        cursor = conn.execute(
            """
            INSERT INTO users (
                email,
                password_hash,
                password_salt,
                approved,
                is_employee,
                is_management,
                is_admin,
                created_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                normalized_email,
                password_hash,
                salt_hex,
                approved,
                is_employee,
                is_management,
                is_admin,
                created_at,
            ),
        )
        user_id = int(cursor.lastrowid)

        row = conn.execute("SELECT * FROM users WHERE id = ?", (user_id,)).fetchone()
        return _row_to_user(row) or {}


def _get_user_row_by_email(conn: sqlite3.Connection, email: str) -> sqlite3.Row | None:
    normalized_email = email.strip().lower()
    return conn.execute("SELECT * FROM users WHERE email = ?", (normalized_email,)).fetchone()


def verify_user_credentials(email: str, password: str) -> Optional[Dict[str, Any]]:
    with get_connection() as conn:
        row = _get_user_row_by_email(conn, email)
        if row is None:
            return None

        expected_hash = _hash_password(password, row["password_salt"])
        if not secrets.compare_digest(expected_hash, row["password_hash"]):
            return None

        return _row_to_user(row)


def create_session(user_id: int) -> str:
    token = uuid4().hex
    created_at = _utc_now()
    expires_at = created_at + timedelta(days=SESSION_DURATION_DAYS)

    with get_connection() as conn:
        conn.execute(
            """
            INSERT INTO sessions (token, user_id, created_at, expires_at)
            VALUES (?, ?, ?, ?)
            """,
            (token, user_id, created_at.isoformat(), expires_at.isoformat()),
        )
        conn.execute(
            "UPDATE users SET last_login_at = ? WHERE id = ?",
            (created_at.isoformat(), user_id),
        )
    return token


def get_user_by_session(token: str) -> Optional[Dict[str, Any]]:
    with get_connection() as conn:
        row = conn.execute(
            """
            SELECT users.*
            FROM sessions
            JOIN users ON users.id = sessions.user_id
            WHERE sessions.token = ?
            """,
            (token,),
        ).fetchone()
        if row is None:
            return None

        session = conn.execute(
            "SELECT expires_at FROM sessions WHERE token = ?",
            (token,),
        ).fetchone()
        if session is None:
            return None

        expires_at = datetime.fromisoformat(session["expires_at"])
        if expires_at <= _utc_now():
            conn.execute("DELETE FROM sessions WHERE token = ?", (token,))
            return None

        return _row_to_user(row)


def delete_session(token: str) -> None:
    with get_connection() as conn:
        conn.execute("DELETE FROM sessions WHERE token = ?", (token,))


def list_users() -> List[Dict[str, Any]]:
    with get_connection() as conn:
        rows = conn.execute(
            """
            SELECT *
            FROM users
            ORDER BY approved ASC, created_at DESC
            """
        ).fetchall()
        return [_row_to_user(row) for row in rows if row is not None]


def update_user_access(
    user_id: int,
    approved: bool,
    is_employee: bool,
    is_management: bool,
) -> Optional[Dict[str, Any]]:
    with get_connection() as conn:
        conn.execute(
            """
            UPDATE users
            SET approved = ?, is_employee = ?, is_management = ?
            WHERE id = ?
            """,
            (
                1 if approved else 0,
                1 if is_employee else 0,
                1 if is_management else 0,
                user_id,
            ),
        )
        row = conn.execute("SELECT * FROM users WHERE id = ?", (user_id,)).fetchone()
        return _row_to_user(row)
