"""Tests for src/outlook/messages.py."""
from __future__ import annotations

import json
from unittest.mock import MagicMock, patch

import httpx
import pytest

from src.outlook.messages import get_unread_messages


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_response(status_code: int, body: dict, headers: dict | None = None) -> MagicMock:
    """Build a mock httpx.Response."""
    resp = MagicMock(spec=httpx.Response)
    resp.status_code = status_code
    resp.headers = headers or {}
    resp.json.return_value = body
    resp.raise_for_status = MagicMock()
    if status_code >= 400:
        resp.raise_for_status.side_effect = httpx.HTTPStatusError(
            f"HTTP {status_code}", request=MagicMock(), response=resp
        )
    return resp


# ---------------------------------------------------------------------------
# test_get_unread_messages_empty
# ---------------------------------------------------------------------------


def test_get_unread_messages_empty():
    """Returns an empty list when Graph returns no messages."""
    mock_client = MagicMock(spec=httpx.Client)
    mock_client.__enter__ = lambda s: s
    mock_client.__exit__ = MagicMock(return_value=False)
    mock_client.get.return_value = _make_response(200, {"value": []})

    result = get_unread_messages("fake_token", max_results=10, http=mock_client)
    assert result == []


# ---------------------------------------------------------------------------
# test_get_unread_messages_maps_fields
# ---------------------------------------------------------------------------


def test_get_unread_messages_maps_fields():
    """Maps Graph message fields to the normalised dict format."""
    raw_message = {
        "id": "AAMkABC123",
        "conversationId": "conv-xyz",
        "subject": "Reunión de equipo",
        "from": {
            "emailAddress": {
                "name": "Ana García",
                "address": "ana.garcia@empresa.com",
            }
        },
        "bodyPreview": "Hola equipo, recordad la reunión de mañana...",
        "receivedDateTime": "2026-05-14T09:30:00Z",
    }
    mock_client = MagicMock(spec=httpx.Client)
    mock_client.get.return_value = _make_response(200, {"value": [raw_message]})

    result = get_unread_messages("fake_token", max_results=10, http=mock_client)

    assert len(result) == 1
    msg = result[0]
    assert msg["id"] == "AAMkABC123"
    assert msg["thread_id"] == "conv-xyz"
    assert msg["subject"] == "Reunión de equipo"
    assert "Ana García" in msg["sender"]
    assert "ana.garcia@empresa.com" in msg["sender"]
    assert msg["snippet"] == "Hola equipo, recordad la reunión de mañana..."
    assert msg["date"] == "2026-05-14T09:30:00Z"


# ---------------------------------------------------------------------------
# test_get_unread_messages_429_retry
# ---------------------------------------------------------------------------


def test_get_unread_messages_429_retry():
    """Retries once on 429 using Retry-After header and returns results."""
    raw_message = {
        "id": "msg-001",
        "conversationId": "conv-001",
        "subject": "Test Subject",
        "from": {"emailAddress": {"name": "Test Sender", "address": "test@example.com"}},
        "bodyPreview": "Test preview",
        "receivedDateTime": "2026-05-14T10:00:00Z",
    }

    first_response = _make_response(429, {}, headers={"Retry-After": "1"})
    first_response.raise_for_status = MagicMock()  # Don't raise on 429 check

    second_response = _make_response(200, {"value": [raw_message]})

    mock_client = MagicMock(spec=httpx.Client)
    mock_client.get.side_effect = [first_response, second_response]

    with patch("src.outlook.messages.time.sleep") as mock_sleep:
        result = get_unread_messages("fake_token", max_results=10, http=mock_client)

    mock_sleep.assert_called_once_with(1)
    assert len(result) == 1
    assert result[0]["id"] == "msg-001"
