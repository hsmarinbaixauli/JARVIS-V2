"""SQLite database connection and schema management. Provides init_db() to
create tables on first run and get_connection() to return a connection.
Tables: conversations (id, title, created_at) and messages (id,
conversation_id, role, content, tool_calls_json, timestamp)."""
from __future__ import annotations


def init_db() -> None:
    pass


def get_connection():
    pass
