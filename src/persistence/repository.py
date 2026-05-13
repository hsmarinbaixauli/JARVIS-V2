"""CRUD operations for conversations and messages."""
from __future__ import annotations

import json
from datetime import datetime, timezone
from typing import Any
from uuid import uuid4

from src.persistence.database import get_connection
from src.persistence.models import Conversation, Message


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


# ---------------------------------------------------------------------------
# Conversations
# ---------------------------------------------------------------------------

def create_conversation(conversation_id: str, title: str = "") -> Conversation:
    """Insert a new conversation row and return it."""
    ts = _now()
    with get_connection() as conn:
        conn.execute(
            "INSERT OR IGNORE INTO conversations (id, title, created_at) VALUES (?, ?, ?)",
            (conversation_id, title[:200], ts),
        )
    return Conversation(id=conversation_id, title=title[:200], created_at=ts)


def get_conversation(conversation_id: str) -> Conversation | None:
    with get_connection() as conn:
        row = conn.execute(
            "SELECT id, title, created_at FROM conversations WHERE id = ?",
            (conversation_id,),
        ).fetchone()
    if row is None:
        return None
    return Conversation(id=row["id"], title=row["title"], created_at=row["created_at"])


def list_conversations() -> list[Conversation]:
    """Return all conversations newest-first."""
    with get_connection() as conn:
        rows = conn.execute(
            "SELECT id, title, created_at FROM conversations ORDER BY created_at DESC"
        ).fetchall()
    return [Conversation(id=r["id"], title=r["title"], created_at=r["created_at"]) for r in rows]


def delete_conversation(conversation_id: str) -> None:
    """Delete a conversation and all its messages (cascade)."""
    with get_connection() as conn:
        conn.execute("DELETE FROM conversations WHERE id = ?", (conversation_id,))


# ---------------------------------------------------------------------------
# Messages
# ---------------------------------------------------------------------------

def save_message(
    conversation_id: str,
    role: str,
    content: str,
    tool_calls_json: str | None = None,
) -> Message:
    """Insert a message row and return it."""
    msg_id = str(uuid4())
    ts = _now()
    with get_connection() as conn:
        conn.execute(
            """INSERT INTO messages
               (id, conversation_id, role, content, tool_calls_json, timestamp)
               VALUES (?, ?, ?, ?, ?, ?)""",
            (msg_id, conversation_id, role, content, tool_calls_json, ts),
        )
    return Message(
        id=msg_id,
        conversation_id=conversation_id,
        role=role,
        content=content,
        tool_calls_json=tool_calls_json,
        timestamp=ts,
    )


def get_messages(conversation_id: str) -> list[Message]:
    """Return all Message dataclasses for a conversation, oldest-first."""
    with get_connection() as conn:
        rows = conn.execute(
            """SELECT id, conversation_id, role, content, tool_calls_json, timestamp
               FROM messages WHERE conversation_id = ? ORDER BY timestamp ASC""",
            (conversation_id,),
        ).fetchall()
    return [
        Message(
            id=r["id"],
            conversation_id=r["conversation_id"],
            role=r["role"],
            content=r["content"],
            tool_calls_json=r["tool_calls_json"],
            timestamp=r["timestamp"],
        )
        for r in rows
    ]


def get_history(conversation_id: str) -> list[dict[str, Any]]:
    """Return Claude-format message dicts for a conversation, oldest-first.

    Each entry is {"role": "user"|"assistant", "content": "<text>"}.
    Used directly as the history= parameter passed to orchestrator.run().
    """
    messages = get_messages(conversation_id)
    return [{"role": m.role, "content": m.content} for m in messages]


def clear_conversation(conversation_id: str) -> None:
    """Delete all messages for a conversation but keep the conversation record."""
    with get_connection() as conn:
        conn.execute("DELETE FROM messages WHERE conversation_id = ?", (conversation_id,))


def prune_old_conversations(days: int = 30) -> int:
    """Delete conversations (and their messages) older than *days*. Returns count."""
    cutoff = datetime.now(timezone.utc).replace(
        hour=0, minute=0, second=0, microsecond=0
    )
    from datetime import timedelta
    cutoff -= timedelta(days=days)
    cutoff_str = cutoff.isoformat()
    with get_connection() as conn:
        count = conn.execute(
            "SELECT COUNT(*) FROM conversations WHERE created_at < ?", (cutoff_str,)
        ).fetchone()[0]
        conn.execute("DELETE FROM conversations WHERE created_at < ?", (cutoff_str,))
    return count
