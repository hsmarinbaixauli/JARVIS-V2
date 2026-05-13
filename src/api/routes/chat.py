"""Chat and conversation endpoints.

POST   /api/chat                            — blocking full-response chat.
GET    /api/chat/stream                     — SSE streaming chat (Step 5).
GET    /api/conversations                   — list all sessions.
GET    /api/conversations/{id}/messages     — full message history.
DELETE /api/conversations/{id}              — delete session and messages.
"""
from __future__ import annotations

import json
from uuid import uuid4

from fastapi import APIRouter, Depends, HTTPException, status

from src.api.dependencies import get_services
from src.api.models import ChatRequest, ChatResponse, ConversationSummary, MessageRecord
from src.orchestrator.agent import run
from src.persistence import repository as repo

router = APIRouter()


@router.post("/chat", response_model=ChatResponse)
def chat(
    req: ChatRequest,
    services: dict = Depends(get_services),
) -> ChatResponse:
    """Blocking chat with SQLite-backed conversation history."""
    conversation_id = req.conversation_id or str(uuid4())

    # Create the conversation record on first message.
    if repo.get_conversation(conversation_id) is None:
        repo.create_conversation(conversation_id, title=req.message[:80].strip())

    history = repo.get_history(conversation_id)

    try:
        reply, tool_log = run(
            message=req.message,
            history=history,
            services=services,
        )
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(exc),
        ) from exc

    final_reply = reply or "Lo siento, no pude generar una respuesta."

    # Persist both turns so history is available next request.
    repo.save_message(conversation_id, role="user", content=req.message)
    repo.save_message(
        conversation_id,
        role="assistant",
        content=final_reply,
        tool_calls_json=json.dumps(tool_log) if tool_log else None,
    )

    return ChatResponse(
        reply=final_reply,
        conversation_id=conversation_id,
        tool_calls=tool_log,
    )


# ---------------------------------------------------------------------------
# Conversation management
# ---------------------------------------------------------------------------

@router.get("/conversations", response_model=list[ConversationSummary])
def list_conversations() -> list[ConversationSummary]:
    """List all conversations newest-first."""
    convs = repo.list_conversations()
    return [
        ConversationSummary(id=c.id, title=c.title, created_at=c.created_at)
        for c in convs
    ]


@router.get("/conversations/{conversation_id}/messages", response_model=list[MessageRecord])
def get_conversation_messages(conversation_id: str) -> list[MessageRecord]:
    """Return all messages for a conversation oldest-first."""
    if repo.get_conversation(conversation_id) is None:
        raise HTTPException(status_code=404, detail="Conversation not found.")
    messages = repo.get_messages(conversation_id)
    return [
        MessageRecord(id=m.id, role=m.role, content=m.content, timestamp=m.timestamp)
        for m in messages
    ]


@router.delete("/conversations/{conversation_id}")
def delete_conversation(conversation_id: str) -> dict:
    """Delete a conversation and all its messages."""
    if repo.get_conversation(conversation_id) is None:
        raise HTTPException(status_code=404, detail="Conversation not found.")
    repo.delete_conversation(conversation_id)
    return {"status": "deleted"}
