"""Microsoft Graph email operations for Outlook.

Provides functions to fetch, mark, and reply to messages via the
/v1.0/me/messages Graph endpoint.

Public API:
    get_unread_messages(access_token, max_results, http) -> list[dict]
    mark_as_read(access_token, message_id, http) -> None
    send_reply(access_token, message_id, body_text, http) -> dict
"""
from __future__ import annotations

import logging
import time
from typing import Any

import httpx

_log = logging.getLogger(__name__)

_GRAPH_BASE = "https://graph.microsoft.com/v1.0"


def get_unread_messages(
    access_token: str,
    max_results: int = 10,
    http: httpx.Client | None = None,
) -> list[dict[str, Any]]:
    """Fetch unread messages from the Outlook Inbox via Microsoft Graph.

    Args:
        access_token: A valid Bearer token with Mail.Read scope.
        max_results: Maximum number of messages to return (1–25).
        http: Optional pre-constructed httpx.Client (injected in tests).

    Returns:
        A list of normalised message dicts with keys:
        id, thread_id, subject, sender, snippet, date.

    Raises:
        RuntimeError: If Graph returns 429 twice in a row.
    """
    url = (
        f"{_GRAPH_BASE}/me/mailFolders/Inbox/messages"
        f"?$filter=isRead eq false"
        f"&$top={max_results}"
        f"&$select=id,conversationId,subject,from,bodyPreview,receivedDateTime"
        f"&$orderby=receivedDateTime desc"
    )
    headers = {
        "Authorization": f"Bearer {access_token}",
        "Accept": "application/json",
    }

    _own_client = http is None
    client = http or httpx.Client(timeout=30)

    try:
        results: list[dict[str, Any]] = []

        while url and len(results) < max_results:
            response = _get_with_retry(client, url, headers)
            data = response.json()
            messages = data.get("value", [])
            for msg in messages:
                if len(results) >= max_results:
                    break
                results.append(_normalize_message(msg))
            url = data.get("@odata.nextLink")  # type: ignore[assignment]

        return results
    finally:
        if _own_client:
            client.close()


def mark_as_read(
    access_token: str,
    message_id: str,
    http: httpx.Client | None = None,
) -> None:
    """Mark a message as read via PATCH /v1.0/me/messages/{id}.

    Args:
        access_token: A valid Bearer token with Mail.ReadWrite scope.
        message_id: The Graph message ID to mark as read.
        http: Optional pre-constructed httpx.Client (injected in tests).
    """
    url = f"{_GRAPH_BASE}/me/messages/{message_id}"
    headers = {
        "Authorization": f"Bearer {access_token}",
        "Content-Type": "application/json",
    }
    _own_client = http is None
    client = http or httpx.Client(timeout=30)
    try:
        response = client.patch(url, headers=headers, json={"isRead": True})
        response.raise_for_status()
    finally:
        if _own_client:
            client.close()


def send_reply(
    access_token: str,
    message_id: str,
    body_text: str,
    http: httpx.Client | None = None,
) -> dict:
    """Send a plain-text reply to a message via Graph.

    Args:
        access_token: A valid Bearer token with Mail.Send scope.
        message_id: The Graph message ID to reply to.
        body_text: The plain-text content of the reply.
        http: Optional pre-constructed httpx.Client (injected in tests).

    Returns:
        {"status": "sent"}
    """
    url = f"{_GRAPH_BASE}/me/messages/{message_id}/reply"
    headers = {
        "Authorization": f"Bearer {access_token}",
        "Content-Type": "application/json",
    }
    _own_client = http is None
    client = http or httpx.Client(timeout=30)
    try:
        response = client.post(url, headers=headers, json={"comment": body_text})
        response.raise_for_status()
        return {"status": "sent"}
    finally:
        if _own_client:
            client.close()


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------


def _get_with_retry(client: httpx.Client, url: str, headers: dict) -> httpx.Response:
    """Perform a GET with one 429 retry using the Retry-After header."""
    response = client.get(url, headers=headers)
    if response.status_code == 429:
        retry_after = int(response.headers.get("Retry-After", "5"))
        _log.warning("Graph API rate limited; retrying after %ds", retry_after)
        time.sleep(retry_after)
        response = client.get(url, headers=headers)
        if response.status_code == 429:
            raise RuntimeError("Graph API rate limited")
    response.raise_for_status()
    return response


def _normalize_message(msg: dict[str, Any]) -> dict[str, Any]:
    """Map a raw Graph Message object to the normalised dict format."""
    from_obj = msg.get("from", {}).get("emailAddress", {})
    name = from_obj.get("name", "")
    address = from_obj.get("address", "")
    if name and address:
        sender = f"{name} <{address}>"
    elif address:
        sender = address
    else:
        sender = name
    return {
        "id":        msg["id"],
        "thread_id": msg.get("conversationId", ""),
        "subject":   msg.get("subject", "(sin asunto)"),
        "sender":    sender.strip(),
        "snippet":   msg.get("bodyPreview", ""),
        "date":      msg.get("receivedDateTime", ""),
    }
