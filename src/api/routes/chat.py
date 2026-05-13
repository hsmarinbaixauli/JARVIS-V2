"""Chat endpoints. POST /api/chat for blocking full-response chat. GET
/api/chat/stream for SSE streaming chat. GET /api/conversations and GET
/api/conversations/{id}/messages for history. DELETE /api/conversations/{id}
to remove a conversation."""
from __future__ import annotations
