"""Claude agentic loop for Jarvis V2.

Provides run() (blocking) which drives a full multi-turn Claude conversation
with tool use and returns the final text reply.  Ported and refactored from
_run_agentic_turn() in the legacy src/main.py.

run_streaming() (async generator yielding SSE events) is added in Step 5.
"""
from __future__ import annotations

import logging
from typing import Any

import anthropic

from src.orchestrator.dispatcher import dispatch
from src.orchestrator.prompts import MAX_TOKENS, MAX_TOOL_ITERATIONS, MODEL, SYSTEM_PROMPT
from src.tools.definitions import get_active_tools

_log = logging.getLogger(__name__)


def run(
    message: str,
    history: list[dict[str, Any]],
    services: dict[str, Any],
) -> tuple[str, list[dict[str, Any]]]:
    """Send *message* to Claude and handle the full tool-use loop.

    Args:
        message: The user's chat message text.
        history: Conversation history as a list of Claude message dicts
                 ({"role": "user"|"assistant", "content": ...}).
                 Pass [] for a fresh conversation (no persistence in Step 3).
        services: Dict with keys: anthropic, calendar, gmail, spotify, erp.

    Returns:
        A tuple of (reply_text, tool_log).
        reply_text is the final plain-text response from Claude.
        tool_log is a list of dicts recording each tool call made.
    """
    client: anthropic.Anthropic = services["anthropic"]
    tools = get_active_tools()

    messages: list[dict[str, Any]] = list(history) + [{"role": "user", "content": message}]
    tool_log: list[dict[str, Any]] = []

    response = client.messages.create(
        model=MODEL,
        max_tokens=MAX_TOKENS,
        system=SYSTEM_PROMPT,
        tools=tools,
        messages=messages,
    )

    iterations = 0
    while response.stop_reason == "tool_use" and iterations < MAX_TOOL_ITERATIONS:
        iterations += 1

        tool_calls = [b for b in response.content if b.type == "tool_use"]
        tool_results: list[dict[str, Any]] = []

        for tool in tool_calls:
            try:
                result = dispatch(tool.name, tool.input, services)
                content = str(result)
                tool_log.append({"name": tool.name, "input": tool.input,
                                  "result": content, "error": None})
            except Exception as exc:
                content = f"Error: {exc}"
                tool_log.append({"name": tool.name, "input": tool.input,
                                  "result": None, "error": str(exc)})
                _log.warning("Tool %r raised: %s", tool.name, exc)

            tool_results.append({
                "type": "tool_result",
                "tool_use_id": tool.id,
                "content": content,
            })

        messages.append({"role": "assistant", "content": response.content})
        messages.append({"role": "user", "content": tool_results})

        response = client.messages.create(
            model=MODEL,
            max_tokens=MAX_TOKENS,
            system=SYSTEM_PROMPT,
            tools=tools,
            messages=messages,
        )

    if iterations >= MAX_TOOL_ITERATIONS:
        _log.warning("Tool-use loop hit iteration limit (%d).", MAX_TOOL_ITERATIONS)

    if response.stop_reason == "max_tokens":
        _log.warning("Claude response truncated at max_tokens.")
        return "Lo siento, la respuesta era demasiado larga. Intenta una pregunta más concreta.", tool_log

    text_parts = [b.text for b in response.content if hasattr(b, "type") and b.type == "text"]
    return "\n".join(text_parts), tool_log


async def run_streaming():
    """Async generator yielding SSE-compatible dicts. Implemented in Step 5."""
    raise NotImplementedError("Streaming implemented in Step 5.")
