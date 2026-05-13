"""Claude agentic loop. Provides run() (blocking, returns full text + tool log)
and run_streaming() (async generator yielding SSE-compatible dicts) for driving
a multi-turn Claude conversation with tool use. Replaces the
_run_agentic_turn() function from the legacy src/main.py."""
from __future__ import annotations


def run():
    pass


async def run_streaming():
    pass
