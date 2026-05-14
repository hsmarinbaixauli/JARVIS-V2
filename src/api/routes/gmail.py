"""Gmail endpoints.

GET  /api/gmail/summary?max_results=10
    Fetches unread emails and returns a Spanish AI-generated digest.
    Returns mock/demo data when Gmail credentials are not configured,
    so the endpoint is always available.

POST /api/gmail/mark-read
    Marks a message as read by message_id.
    Body: {"message_id": "<gmail-message-id>"}
"""
from __future__ import annotations

import logging
import os

import anthropic
from fastapi import APIRouter, HTTPException, Query, status
from pydantic import BaseModel

from src.gmail.summarizer import GmailSummary, EmailItem, summarize_emails

_log = logging.getLogger(__name__)
router = APIRouter()


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _get_anthropic_client() -> anthropic.Anthropic:
    """Return an Anthropic client using ANTHROPIC_API_KEY from the environment."""
    api_key = os.getenv("ANTHROPIC_API_KEY")
    if not api_key:
        raise RuntimeError("ANTHROPIC_API_KEY environment variable is not set.")
    return anthropic.Anthropic(api_key=api_key)


def _mock_summary(max_results: int) -> GmailSummary:
    """Return demo data so the endpoint always returns valid JSON."""
    demo_emails = [
        EmailItem(
            urgencia="alta",
            resumen_breve="Reunión urgente mañana a las 9:00 con el equipo de ventas.",
            accion_sugerida="Confirmar asistencia y preparar presentación de resultados.",
        ),
        EmailItem(
            urgencia="media",
            resumen_breve="Factura pendiente de aprobación por 1.250 €.",
            accion_sugerida="Revisar factura y aprobar o rechazar antes del viernes.",
        ),
        EmailItem(
            urgencia="baja",
            resumen_breve="Newsletter mensual con novedades del sector.",
            accion_sugerida="Leer cuando haya tiempo disponible.",
        ),
    ]
    count = min(max_results, len(demo_emails))
    return GmailSummary(
        resumen_general=(
            "DEMO — credenciales de Gmail no configuradas. "
            "Tienes correos urgentes que requieren atención: "
            "una reunión de equipo y una factura pendiente de aprobación."
        ),
        total_no_leidos=count,
        correos=demo_emails[:count],
    )


# ---------------------------------------------------------------------------
# Routes
# ---------------------------------------------------------------------------

@router.get("/gmail/summary", response_model=GmailSummary)
async def gmail_summary(
    max_results: int = Query(default=10, ge=1, le=25),
) -> GmailSummary:
    """Return a Spanish AI-generated digest of unread Gmail messages.

    Falls back to demo data when Gmail credentials or the Anthropic API key
    are not available, so the endpoint always returns valid JSON.
    """
    # Attempt to use real Gmail credentials.
    try:
        from src.gmail.auth import get_gmail_service
        from src.gmail.messages import get_unread_messages

        service = get_gmail_service()
        emails = get_unread_messages(service, max_results=max_results)
    except FileNotFoundError:
        _log.info("Gmail credentials not found — returning demo data.")
        return _mock_summary(max_results)
    except Exception as exc:  # noqa: BLE001
        _log.warning("Could not connect to Gmail (%s) — returning demo data.", exc)
        return _mock_summary(max_results)

    # Summarise with Claude Haiku.
    try:
        client = _get_anthropic_client()
        return await summarize_emails(emails, client)
    except RuntimeError as exc:
        # ANTHROPIC_API_KEY missing — fall back to a plain (non-AI) summary.
        _log.warning("Anthropic client unavailable (%s) — returning plain summary.", exc)
        from src.gmail.summarizer import _fallback_summary
        return _fallback_summary(emails)
    except Exception as exc:  # noqa: BLE001
        _log.error("summarize_emails raised an unexpected error: %s", exc)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="No se pudo generar el resumen de correos.",
        ) from exc


class MarkReadRequest(BaseModel):
    message_id: str


@router.post("/gmail/mark-read", status_code=status.HTTP_200_OK)
def gmail_mark_read(body: MarkReadRequest) -> dict:
    """Mark a Gmail message as read.

    Requires Gmail credentials to be configured.  Returns 503 when
    credentials are not available.
    """
    try:
        from src.gmail.auth import get_gmail_service
        from src.gmail.messages import mark_as_read

        service = get_gmail_service()
        mark_as_read(service, body.message_id)
        return {"status": "ok", "message_id": body.message_id}

    except FileNotFoundError as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Credenciales de Gmail no configuradas.",
        ) from exc
    except Exception as exc:  # noqa: BLE001
        _log.error("mark-read failed for %s: %s", body.message_id, exc)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="No se pudo marcar el correo como leído.",
        ) from exc
