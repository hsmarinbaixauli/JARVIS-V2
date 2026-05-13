"""FastAPI dependency injection providers.

Supplies initialized service clients (Anthropic, Google Calendar, Gmail,
Spotify, ERP) to route handlers via Depends().  All clients are singletons
initialized lazily on the first request and cached for the process lifetime.
"""
from __future__ import annotations

import logging
import os
from typing import Any

from dotenv import load_dotenv

_log = logging.getLogger(__name__)
_services: dict[str, Any] | None = None


def _init_services() -> dict[str, Any]:
    """Initialize all external service clients once.

    Each service is attempted independently — failures are logged as warnings
    so the server starts even when some credentials are missing.  The
    dispatcher returns a user-visible error for any unavailable service.

    Raises:
        RuntimeError: If ANTHROPIC_API_KEY is not set (hard requirement).
    """
    load_dotenv()

    api_key: str | None = os.environ.get("ANTHROPIC_API_KEY")
    if not api_key:
        raise RuntimeError(
            "ANTHROPIC_API_KEY is not set. Add it to your .env file."
        )

    import anthropic
    anthropic_client = anthropic.Anthropic(api_key=api_key)

    calendar = None
    try:
        from src.gcalendar.auth import get_calendar_service
        calendar = get_calendar_service()
        _log.info("Google Calendar: connected.")
    except Exception as exc:
        _log.warning("Google Calendar unavailable: %s", exc)

    gmail = None
    try:
        from src.gmail.auth import get_gmail_service
        gmail = get_gmail_service()
        _log.info("Gmail: connected.")
    except Exception as exc:
        _log.warning("Gmail unavailable: %s", exc)

    spotify = None
    personal_tools = os.environ.get("JARVIS_PERSONAL_TOOLS", "false").strip().lower()
    if personal_tools in ("1", "true", "yes"):
        try:
            from src.spotify.auth import get_spotify_client
            spotify = get_spotify_client()
            _log.info("Spotify: connected.")
        except Exception as exc:
            _log.warning("Spotify unavailable: %s", exc)

    return {
        "anthropic": anthropic_client,
        "calendar": calendar,
        "gmail": gmail,
        "spotify": spotify,
        "erp": None,  # Playwright ERPClient added in Step 10
    }


def get_services() -> dict[str, Any]:
    """Return the singleton services dict, initializing on first call.

    Used as a FastAPI dependency via Depends(get_services).
    """
    global _services
    if _services is None:
        _services = _init_services()
    return _services
