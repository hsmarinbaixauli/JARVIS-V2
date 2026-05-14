"""Outlook / Microsoft Graph endpoints.

GET  /api/outlook/summary?max_results=10
    Fetches unread Outlook emails and returns a Spanish AI-generated digest.
    Returns mock/demo data when Microsoft credentials are not configured,
    so the endpoint is always available.

POST /api/outlook/authenticate
    Starts the MSAL device-code flow and returns verification_uri + user_code.
    The completion step runs in a BackgroundTask.

GET  /api/outlook/auth-status
    Returns {"authenticated": bool}.

POST /api/outlook/mark-read
    Marks an Outlook message as read by message_id.
    Body: {"message_id": "<graph-message-id>"}
"""
from __future__ import annotations

import logging
import os

import anthropic
from fastapi import APIRouter, BackgroundTasks, HTTPException, Query, status
from pydantic import BaseModel

from src.gmail.summarizer import EmailSummary, EmailItem, summarize_emails

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


def _mock_outlook_summary(max_results: int) -> EmailSummary:
    """Return demo Outlook data so the endpoint always returns valid JSON."""
    demo_emails = [
        EmailItem(
            urgencia="alta",
            resumen_breve="Aprobación requerida: contrato con proveedor antes del viernes.",
            accion_sugerida="Revisar el contrato adjunto y aprobar o solicitar cambios.",
        ),
        EmailItem(
            urgencia="media",
            resumen_breve="Informe semanal de ventas Q2 listo para revisión.",
            accion_sugerida="Leer el informe y preparar comentarios para la reunión del lunes.",
        ),
        EmailItem(
            urgencia="baja",
            resumen_breve="Invitación al webinar corporativo sobre transformación digital.",
            accion_sugerida="Valorar asistencia y registrarse si es de interés.",
        ),
    ]
    count = min(max_results, len(demo_emails))
    return EmailSummary(
        resumen_general=(
            "DEMO — Outlook no conectado. "
            "Conecta tu cuenta Microsoft 365 para ver tus correos corporativos reales. "
            "Hay elementos que requieren atención: aprobación de contrato pendiente."
        ),
        total_no_leidos=count,
        correos=demo_emails[:count],
    )


# ---------------------------------------------------------------------------
# Routes
# ---------------------------------------------------------------------------


@router.get("/outlook/summary", response_model=EmailSummary)
async def outlook_summary(
    max_results: int = Query(default=10, ge=1, le=25),
) -> EmailSummary:
    """Return a Spanish AI-generated digest of unread Outlook messages.

    Falls back to demo data when Outlook credentials or the Anthropic API key
    are not available, so the endpoint always returns valid JSON.
    """
    try:
        from src.outlook.auth import is_authenticated, get_outlook_token
        from src.outlook.messages import get_unread_messages

        if not is_authenticated():
            return _mock_outlook_summary(max_results)

        token = get_outlook_token()
        emails = get_unread_messages(token, max_results=max_results)
    except Exception as exc:  # noqa: BLE001
        _log.warning("Could not connect to Outlook (%s) — returning demo data.", exc)
        return _mock_outlook_summary(max_results)

    try:
        client = _get_anthropic_client()
        return await summarize_emails(emails, client)
    except RuntimeError as exc:
        _log.warning("Anthropic client unavailable (%s) — returning plain summary.", exc)
        from src.gmail.summarizer import _fallback_summary
        return _fallback_summary(emails)
    except Exception as exc:  # noqa: BLE001
        _log.error("summarize_emails raised an unexpected error: %s", exc)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="No se pudo generar el resumen de correos de Outlook.",
        ) from exc


@router.post("/outlook/authenticate")
async def outlook_authenticate(bg: BackgroundTasks) -> dict:
    """Start the MSAL device-code flow.

    Returns the verification_uri and user_code the user must enter at
    https://microsoft.com/devicelogin. The token-completion step is run
    as a background task (MSAL blocks internally while polling Azure).

    Raises:
        HTTP 503: If AZURE_CLIENT_ID is not configured.
    """
    try:
        from src.outlook.auth import start_device_code_flow, complete_device_code_flow
        flow = start_device_code_flow()
        bg.add_task(complete_device_code_flow, flow)
        return {
            "verification_uri": flow["verification_uri"],
            "user_code":        flow["user_code"],
            "expires_in":       flow.get("expires_in", 900),
            "message":          flow.get("message", ""),
        }
    except RuntimeError as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="AZURE_CLIENT_ID no configurado.",
        ) from exc


@router.get("/outlook/auth-status")
def outlook_auth_status() -> dict:
    """Return whether a valid Outlook token is cached."""
    from src.outlook.auth import is_authenticated
    return {"authenticated": is_authenticated()}


class MarkReadRequest(BaseModel):
    message_id: str


@router.post("/outlook/mark-read", status_code=status.HTTP_200_OK)
def outlook_mark_read(body: MarkReadRequest) -> dict:
    """Mark an Outlook message as read.

    Requires a valid Outlook token. Returns 503 when not authenticated.
    """
    try:
        from src.outlook.auth import is_authenticated, get_outlook_token
        from src.outlook.messages import mark_as_read

        if not is_authenticated():
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="Outlook no autenticado. Conecta tu cuenta Microsoft 365.",
            )
        token = get_outlook_token()
        mark_as_read(token, body.message_id)
        return {"status": "ok", "message_id": body.message_id}

    except HTTPException:
        raise
    except Exception as exc:  # noqa: BLE001
        _log.error("outlook mark-read failed for %s: %s", body.message_id, exc)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="No se pudo marcar el correo de Outlook como leído.",
        ) from exc
