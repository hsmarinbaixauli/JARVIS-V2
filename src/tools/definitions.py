"""Anthropic tool definitions for Jarvis capabilities.

Exports ``TOOLS`` (full list) and ``get_active_tools()`` (filtered by feature
flags).  This module contains no runtime logic beyond the feature-flag filter.
"""

from __future__ import annotations

import os
from typing import Any


TOOLS: list[dict[str, Any]] = [
    {
        "name": "get_today_events",
        "description": (
            "Get all calendar events scheduled for today from Google Calendar. "
            "Returns events spanning from 00:00:00 to 23:59:59 in the local "
            "system timezone, including all-day events."
        ),
        "input_schema": {
            "type": "object",
            "properties": {},
            "required": [],
        },
    },
    {
        "name": "get_upcoming_events",
        "description": (
            "Get calendar events from now until N days ahead from Google Calendar. "
            "Events are ordered by start time."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "days": {
                    "type": "integer",
                    "description": (
                        "Number of days ahead to look for events, counting from "
                        "the current moment. Defaults to 7."
                    ),
                    "minimum": 1,
                    "maximum": 90,
                },
            },
            "required": [],
        },
    },
    {
        "name": "create_event",
        "description": "Create a new event on the primary Google Calendar.",
        "input_schema": {
            "type": "object",
            "properties": {
                "title": {
                    "type": "string",
                    "description": "The event title or summary shown in the calendar UI.",
                },
                "start_datetime": {
                    "type": "string",
                    "description": (
                        "Event start time in ISO 8601 format: \"YYYY-MM-DDTHH:MM:SS\". "
                        "Example: \"2026-05-05T09:30:00\"."
                    ),
                },
                "end_datetime": {
                    "type": "string",
                    "description": (
                        "Event end time in ISO 8601 format: \"YYYY-MM-DDTHH:MM:SS\". "
                        "Example: \"2026-05-05T10:30:00\"."
                    ),
                },
                "description": {
                    "type": "string",
                    "description": (
                        "Optional free-text body description for the event. "
                        "Defaults to an empty string."
                    ),
                },
            },
            "required": ["title", "start_datetime", "end_datetime"],
        },
    },
    {
        "name": "get_unread_emails",
        "description": (
            "Fetch unread emails from the user's Gmail inbox. Returns a list with "
            "id, subject, sender, snippet, and date for each unread message. "
            "Use this whenever the user asks to check, read, or summarize their email."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "max_results": {
                    "type": "integer",
                    "description": "Maximum number of unread messages to return. Defaults to 10.",
                    "minimum": 1,
                    "maximum": 25,
                },
            },
            "required": [],
        },
    },
    {
        "name": "get_unread_outlook_emails",
        "description": (
            "Fetch unread emails from the user's Microsoft 365 Outlook inbox via Microsoft Graph. "
            "Returns a list with id, subject, sender, snippet, and date for each unread message. "
            "Use this when the user mentions Outlook, work email, Microsoft 365, or their corporate inbox. "
            "For Gmail use get_unread_emails instead."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "max_results": {
                    "type": "integer",
                    "description": "Maximum number of unread messages to return (1–25). Defaults to 10.",
                    "minimum": 1,
                    "maximum": 25,
                },
            },
            "required": [],
        },
    },
    {
        "name": "send_email_reply",
        "description": (
            "Send a plain-text reply to a specific email message. "
            "IMPORTANT: Always show the recipient and the full proposed reply body "
            "to the user and wait for explicit confirmation before calling this tool."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "message_id": {
                    "type": "string",
                    "description": "The id of the message to reply to, as returned by get_unread_emails.",
                },
                "body_text": {
                    "type": "string",
                    "description": "The plain-text body of the reply (max 5000 characters).",
                },
            },
            "required": ["message_id", "body_text"],
        },
    },
    {
        "name": "mark_email_read",
        "description": "Mark a single email as read.",
        "input_schema": {
            "type": "object",
            "properties": {
                "message_id": {
                    "type": "string",
                    "description": "The id of the message to mark as read.",
                },
            },
            "required": ["message_id"],
        },
    },
    # --- Personal tools (gated by JARVIS_PERSONAL_TOOLS) ---
    {
        "name": "get_current_weather",
        "description": (
            "Get the current weather for a city using OpenWeatherMap. "
            "Returns temperature, a short Spanish description, humidity and wind. "
            "Use when the user asks about weather, temperature, rain, or whether to take an umbrella."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "city": {
                    "type": "string",
                    "description": (
                        "City in OpenWeatherMap format, e.g. \"Valencia,ES\". "
                        "Defaults to OPENWEATHER_CITY env var if omitted."
                    ),
                },
                "units": {
                    "type": "string",
                    "enum": ["metric", "imperial"],
                    "description": "Temperature units. Defaults to \"metric\" (Celsius).",
                },
            },
            "required": [],
        },
    },
    {
        "name": "spotify_play",
        "description": (
            "Start or resume Spotify playback. "
            "Use artist + track for a specific song, artist alone for top tracks, "
            "or query for genre/mood/playlist search. Omit all three to resume."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "artist": {"type": "string", "description": "Artist name with correct spelling."},
                "track": {"type": "string", "description": "Song title. Combine with artist for precise match."},
                "query": {"type": "string", "description": "Free-text genre/mood search, e.g. 'jazz', 'lofi'."},
            },
            "required": [],
        },
    },
    {
        "name": "spotify_pause",
        "description": "Pause Spotify playback on the active device.",
        "input_schema": {"type": "object", "properties": {}, "required": []},
    },
    {
        "name": "spotify_next",
        "description": "Skip to the next track on the active Spotify device.",
        "input_schema": {"type": "object", "properties": {}, "required": []},
    },
    {
        "name": "spotify_previous",
        "description": "Go back to the previous track on the active Spotify device.",
        "input_schema": {"type": "object", "properties": {}, "required": []},
    },
    {
        "name": "spotify_set_volume",
        "description": "Set Spotify volume on the active device (0-100).",
        "input_schema": {
            "type": "object",
            "properties": {
                "volume_percent": {
                    "type": "integer",
                    "minimum": 0,
                    "maximum": 100,
                    "description": "Volume percentage from 0 (mute) to 100 (max).",
                },
            },
            "required": ["volume_percent"],
        },
    },
    {
        "name": "spotify_current_track",
        "description": (
            "Return the currently playing Spotify track (artist, title, album, progress). "
            "Use when the user asks what song is playing."
        ),
        "input_schema": {"type": "object", "properties": {}, "required": []},
    },
    # --- ERP tools ---
    {
        "name": "erp_get_order_status",
        "description": (
            "Look up an order in the Expande ERP by its order ID. "
            "Returns the order status, customer name, date, total, and line items. "
            "Use when the user asks about a specific order number or order ID."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "order_id": {
                    "type": "string",
                    "description": "The ERP order ID or order number to look up.",
                },
            },
            "required": ["order_id"],
        },
    },
    {
        "name": "erp_search_by_customer",
        "description": (
            "Search orders in the Expande ERP by customer name. "
            "Returns a list of matching orders with their ID, status, date, and total. "
            "Use when the user asks about orders for a specific customer or company."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "customer_name": {
                    "type": "string",
                    "description": "Customer or company name to search for.",
                },
                "max_results": {
                    "type": "integer",
                    "description": "Maximum number of orders to return. Defaults to 10.",
                    "minimum": 1,
                    "maximum": 50,
                },
            },
            "required": ["customer_name"],
        },
    },
]

_PERSONAL_TOOL_NAMES: frozenset[str] = frozenset({
    "get_current_weather",
    "spotify_play",
    "spotify_pause",
    "spotify_next",
    "spotify_previous",
    "spotify_set_volume",
    "spotify_current_track",
})


def get_active_tools() -> list[dict[str, Any]]:
    """Return TOOLS filtered by the JARVIS_PERSONAL_TOOLS feature flag.

    When JARVIS_PERSONAL_TOOLS is not set or false, weather and Spotify tools
    are excluded so Claude never attempts to call them.
    """
    flag = os.environ.get("JARVIS_PERSONAL_TOOLS", "false").strip().lower()
    personal_enabled = flag in ("1", "true", "yes")
    if personal_enabled:
        return TOOLS
    return [t for t in TOOLS if t["name"] not in _PERSONAL_TOOL_NAMES]
