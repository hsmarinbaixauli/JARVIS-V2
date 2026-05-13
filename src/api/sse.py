"""Server-Sent Events helpers. Provides build_sse_event() to format SSE data
strings and stream_agent_response() async generator that wraps the orchestrator
agentic loop and yields SSE-formatted events for text deltas, tool_use_start,
tool_use_executing, tool_result, and done."""
from __future__ import annotations


def build_sse_event():
    pass


async def stream_agent_response():
    pass
