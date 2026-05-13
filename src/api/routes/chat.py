"""Chat endpoints.

POST /api/chat              — blocking full-response chat.
GET  /api/chat/stream       — SSE streaming chat (Step 5).
GET  /api/conversations     — list sessions (Step 4).
GET  /api/conversations/{id}/messages — full history (Step 4).
DELETE /api/conversations/{id}        — delete session (Step 4).
"""
from __future__ import annotations

from uuid import uuid4

from fastapi import APIRouter, Depends, HTTPException, status

from src.api.dependencies import get_services
from src.api.models import ChatRequest, ChatResponse
from src.orchestrator.agent import run

router = APIRouter()


@router.post("/chat", response_model=ChatResponse)
def chat(
    req: ChatRequest,
    services: dict = Depends(get_services),
) -> ChatResponse:
    """Blocking chat endpoint — returns the full reply once all tool calls complete.

    Conversation history persistence is added in Step 4; for now each request
    starts a fresh context.
    """
    try:
        reply, tool_log = run(
            message=req.message,
            history=[],  # Step 4 adds SQLite-backed history
            services=services,
        )
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(exc),
        ) from exc

    return ChatResponse(
        reply=reply or "Lo siento, no pude generar una respuesta.",
        conversation_id=req.conversation_id or str(uuid4()),
        tool_calls=tool_log,
    )
