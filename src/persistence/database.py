"""SQLite database connection and schema management."""
from __future__ import annotations

import os
import sqlite3
from contextlib import contextmanager
from pathlib import Path
from typing import Iterator

from dotenv import load_dotenv

# Resolved once at module import time so all callers agree on the path.
load_dotenv()
_DB_PATH: Path = Path(
    os.environ.get("JARVIS_DB_PATH", "")
    or str(Path(__file__).resolve().parents[2] / "jarvis.db")
)

_DDL = """
PRAGMA journal_mode = WAL;
PRAGMA foreign_keys = ON;

CREATE TABLE IF NOT EXISTS conversations (
    id         TEXT PRIMARY KEY,
    title      TEXT NOT NULL DEFAULT '',
    created_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS messages (
    id              TEXT PRIMARY KEY,
    conversation_id TEXT NOT NULL,
    role            TEXT NOT NULL CHECK(role IN ('user', 'assistant')),
    content         TEXT NOT NULL DEFAULT '',
    tool_calls_json TEXT,
    timestamp       TEXT NOT NULL,
    FOREIGN KEY(conversation_id) REFERENCES conversations(id) ON DELETE CASCADE
);

CREATE INDEX IF NOT EXISTS idx_messages_conv_ts
    ON messages(conversation_id, timestamp);
"""


def init_db() -> None:
    """Create tables if they don't exist. Idempotent — safe to call on every startup."""
    _DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(str(_DB_PATH))
    try:
        conn.executescript(_DDL)
    finally:
        conn.close()


@contextmanager
def get_connection() -> Iterator[sqlite3.Connection]:
    """Yield a short-lived SQLite connection.

    Commits on clean exit, rolls back on any exception, always closes.
    Creates a new connection each time — safe for FastAPI's threadpool.
    """
    _DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(str(_DB_PATH), check_same_thread=False)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA foreign_keys=ON")
    try:
        yield conn
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()
