"""Chat and conversation endpoints.

POST   /api/chat                            — blocking full-response chat.
GET    /api/chat/stream                     — SSE streaming chat.
GET    /api/conversations                   — list all sessions.
GET    /api/conversations/{id}/messages     — full message history.
DELETE /api/conversations/{id}              — delete session and messages.
"""
from __future__ import annotations

import asyncio
import json
import logging
from uuid import uuid4

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sse_starlette.sse import EventSourceResponse

from src.api.dependencies import get_services
from src.api.models import ChatRequest, ChatResponse, ConversationSummary, MessageRecord
from src.api.sse import build_sse_event
from src.orchestrator.agent import run, run_streaming
from src.persistence import repository as repo

_log = logging.getLogger(__name__)
router = APIRouter()


# ---------------------------------------------------------------------------
# Blocking chat  (POST /api/chat)
# ---------------------------------------------------------------------------

@router.post("/chat", response_model=ChatResponse)
def chat(
    req: ChatRequest,
    services: dict = Depends(get_services),
) -> ChatResponse:
    """Blocking chat with SQLite-backed conversation history."""
    if len(req.message) > 2000:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Message exceeds 2000 character limit",
        )

    conversation_id = req.conversation_id or str(uuid4())

    if repo.get_conversation(conversation_id) is None:
        repo.create_conversation(conversation_id, title=req.message[:80].strip())

    history = repo.get_history(conversation_id)

    try:
        reply, tool_log = run(message=req.message, history=history, services=services)
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(exc)
        ) from exc

    final_reply = reply or "Lo siento, no pude generar una respuesta."
    repo.save_message(conversation_id, role="user", content=req.message)
    repo.save_message(
        conversation_id, role="assistant", content=final_reply,
        tool_calls_json=json.dumps(tool_log) if tool_log else None,
    )

    return ChatResponse(
        reply=final_reply,
        conversation_id=conversation_id,
        tool_calls=tool_log,
    )


# ---------------------------------------------------------------------------
# Streaming chat  (GET /api/chat/stream)
# ---------------------------------------------------------------------------

@router.get("/chat/stream")
async def chat_stream(
    message: str = Query(..., min_length=1, max_length=2000),
    conversation_id: str | None = Query(default=None),
    services: dict = Depends(get_services),
) -> EventSourceResponse:
    """SSE streaming chat.  Browser opens this with EventSource.

    Events emitted (in order):
      tool_use_start       — Claude is calling a tool
      tool_use_executing   — backend is running the tool
      tool_result          — tool finished
      text_delta           — one streamed text token
      done                 — stream complete (sent after DB write)
      error                — something went wrong (followed by done)
    """
    cid = conversation_id or str(uuid4())
    if repo.get_conversation(cid) is None:
        repo.create_conversation(cid, title=message[:80].strip())
    history = repo.get_history(cid)

    async def event_generator():
        full_text_parts: list[str] = []
        tool_log: list[dict] = []

        try:
            async for event_name, data in run_streaming(message, history, services):
                if event_name == "text_delta":
                    full_text_parts.append(data.get("delta", ""))
                elif event_name == "tool_result":
                    tool_log.append({
                        "name": data.get("name"),
                        "output": data.get("output"),
                        "is_error": data.get("is_error", False),
                    })
                # Skip the internal done — we emit our own after persistence
                if event_name != "done":
                    yield build_sse_event(event_name, data)

        except Exception as exc:
            _log.error("Streaming error for conv %s: %s", cid, exc)
            yield build_sse_event("error", {"message": str(exc)})
            yield build_sse_event("done", {"conversation_id": cid})
            return

        # Persist both turns before telling the client we're done
        final_reply = "".join(full_text_parts) or "Lo siento, no pude generar una respuesta."
        await asyncio.to_thread(repo.save_message, cid, "user", message)
        await asyncio.to_thread(
            repo.save_message, cid, "assistant", final_reply,
            json.dumps(tool_log) if tool_log else None,
        )

        yield build_sse_event("done", {"conversation_id": cid})

    return EventSourceResponse(event_generator())


# ---------------------------------------------------------------------------
# Conversation management
# ---------------------------------------------------------------------------

@router.get("/conversations", response_model=list[ConversationSummary])
def list_conversations() -> list[ConversationSummary]:
    """List all conversations newest-first."""
    return [
        ConversationSummary(id=c.id, title=c.title, created_at=c.created_at)
        for c in repo.list_conversations()
    ]


@router.get("/conversations/{conversation_id}/messages", response_model=list[MessageRecord])
def get_conversation_messages(conversation_id: str) -> list[MessageRecord]:
    """Return all messages for a conversation oldest-first."""
    if repo.get_conversation(conversation_id) is None:
        raise HTTPException(status_code=404, detail="Conversation not found.")
    return [
        MessageRecord(id=m.id, role=m.role, content=m.content, timestamp=m.timestamp)
        for m in repo.get_messages(conversation_id)
    ]


@router.delete("/conversations/{conversation_id}")
def delete_conversation(conversation_id: str) -> dict:
    """Delete a conversation and all its messages."""
    if repo.get_conversation(conversation_id) is None:
        raise HTTPException(status_code=404, detail="Conversation not found.")
    repo.delete_conversation(conversation_id)
    return {"status": "deleted"}
