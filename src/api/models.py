"""Pydantic request and response schemas for all API endpoints."""
from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field


# ---------------------------------------------------------------------------
# Chat
# ---------------------------------------------------------------------------

class ChatRequest(BaseModel):
    message: str = Field(..., min_length=1, max_length=2000)
    conversation_id: str | None = None


class ChatResponse(BaseModel):
    reply: str
    conversation_id: str
    tool_calls: list[dict[str, Any]] = Field(default_factory=list)


# ---------------------------------------------------------------------------
# Conversations (Step 4)
# ---------------------------------------------------------------------------

class ConversationSummary(BaseModel):
    id: str
    title: str
    created_at: str
    preview: str = ""


class MessageRecord(BaseModel):
    id: str
    role: str
    content: str
    timestamp: str


# ---------------------------------------------------------------------------
# Gmail (Step 9)
# ---------------------------------------------------------------------------

class EmailItem(BaseModel):
    id: str
    remitente: str
    asunto: str
    urgencia: str
    resumen_breve: str
    accion_sugerida: str


class GmailSummary(BaseModel):
    resumen_general: str
    total_no_leidos: int
    correos: list[EmailItem] = Field(default_factory=list)


# ---------------------------------------------------------------------------
# ERP (Step 10)
# ---------------------------------------------------------------------------

class ERPOrderLine(BaseModel):
    sku: str = ""
    description: str = ""
    qty: int = 0
    unit_price: str = ""
    line_status: str = ""


class ERPOrderResult(BaseModel):
    found: bool
    order_id: str
    status: str = ""
    customer: str = ""
    date: str = ""
    total: str = ""
    lines: list[ERPOrderLine] = Field(default_factory=list)


class ERPSearchResult(BaseModel):
    order_id: str
    customer: str
    status: str
    date: str
