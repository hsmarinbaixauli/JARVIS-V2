"""Server-Sent Events helpers.

build_sse_event() formats a named SSE event for sse_starlette's EventSourceResponse.
Data is JSON-serialised here so the browser receives valid JSON in every
`data:` line — sse_starlette's default str() serialisation produces Python repr
(single-quoted keys) which EventSource.addEventListener can't JSON.parse().

Event types used in Jarvis V2:
  text_delta        — one streamed text chunk from Claude
  tool_use_start    — Claude is about to call a tool (name + id emitted)
  tool_use_executing — backend is executing the tool (shows spinner in UI)
  tool_result       — tool finished, structured output available
  error             — recoverable stream error
  done              — stream complete (always last; includes conversation_id)
"""
from __future__ import annotations

import json
from typing import Any


def build_sse_event(event_name: str, data: dict[str, Any]) -> dict[str, Any]:
    """Return an SSE event dict consumable by sse_starlette EventSourceResponse.

    The data dict is JSON-serialised so sse_starlette emits:
        event: <event_name>
        data: <valid-json-string>
    """
    return {"event": event_name, "data": json.dumps(data, ensure_ascii=False)}
