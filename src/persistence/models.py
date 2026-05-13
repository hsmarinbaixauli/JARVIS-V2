"""Dataclass models mirroring the SQLite persistence schema."""
from __future__ import annotations

from dataclasses import dataclass


@dataclass
class Conversation:
    id: str
    title: str
    created_at: str  # ISO 8601


@dataclass
class Message:
    id: str
    conversation_id: str
    role: str            # "user" | "assistant"
    content: str
    tool_calls_json: str | None  # JSON array, assistant turns only
    timestamp: str       # ISO 8601
