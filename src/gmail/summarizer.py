"""Gmail email summarization using Claude.

Provides summarize_emails(emails, anthropic_client) which calls
claude-haiku-4-5 with a Spanish-language system prompt to produce a
structured JSON digest of unread emails.

Returns an EmailSummary with:
- resumen_general: overall Spanish summary string
- total_no_leidos: integer count of unread emails
- correos: list of EmailItem records, each with urgencia,
  resumen_breve, and accion_sugerida fields.
"""
from __future__ import annotations

import json
import logging
from typing import Any, Literal

from pydantic import BaseModel

_log = logging.getLogger(__name__)

_HAIKU_MODEL = "claude-haiku-4-5"

_SYSTEM_PROMPT = """Eres un asistente ejecutivo que resume correos electrónicos en español.
Se te proporcionará una lista de correos no leídos en formato JSON.

Tu tarea es analizar estos correos y devolver ÚNICAMENTE un objeto JSON válido con esta estructura exacta:
{
  "resumen_general": "<resumen ejecutivo breve en español de todos los correos>",
  "total_no_leidos": <número entero>,
  "correos": [
    {
      "urgencia": "<alta|media|baja>",
      "resumen_breve": "<resumen de una o dos frases en español>",
      "accion_sugerida": "<acción concreta recomendada en español>"
    }
  ]
}

Reglas:
- Responde SOLO con el JSON, sin texto adicional, sin bloques de código.
- El campo "urgencia" debe ser exactamente "alta", "media" o "baja".
- Ordena los correos en el array de mayor a menor urgencia.
- Si no hay correos, devuelve total_no_leidos=0 y correos=[].
- Todos los textos deben estar en español."""


class EmailItem(BaseModel):
    urgencia: Literal["alta", "media", "baja"]
    resumen_breve: str
    accion_sugerida: str


class EmailSummary(BaseModel):
    resumen_general: str
    total_no_leidos: int
    correos: list[EmailItem]


GmailSummary = EmailSummary  # backwards-compat


async def summarize_emails(
    emails: list[dict[str, Any]],
    anthropic_client: Any,
) -> EmailSummary:
    """Call Claude Haiku with a Spanish summarization prompt.

    Args:
        emails: List of normalised email dicts from get_unread_messages.
                Each dict has: id, thread_id, subject, sender, snippet, date.
        anthropic_client: An initialised anthropic.Anthropic() (or AsyncAnthropic)
                          client instance.

    Returns:
        A validated GmailSummary Pydantic model.
    """
    if not emails:
        return EmailSummary(
            resumen_general="No hay correos no leídos en este momento.",
            total_no_leidos=0,
            correos=[],
        )

    # Build a compact representation of the emails for the prompt.
    email_data = [
        {
            "id": e.get("id", ""),
            "asunto": e.get("subject", "(sin asunto)"),
            "remitente": e.get("sender", "(desconocido)"),
            "fecha": e.get("date", ""),
            "extracto": e.get("snippet", ""),
        }
        for e in emails
    ]

    user_content = (
        f"Tienes {len(emails)} correo(s) no leído(s):\n\n"
        + json.dumps(email_data, ensure_ascii=False, indent=2)
    )

    try:
        response = anthropic_client.messages.create(
            model=_HAIKU_MODEL,
            max_tokens=2048,
            system=_SYSTEM_PROMPT,
            messages=[{"role": "user", "content": user_content}],
        )

        raw_text = next(
            (block.text for block in response.content if block.type == "text"),
            "",
        )

        parsed = json.loads(raw_text)
        return EmailSummary(**parsed)

    except json.JSONDecodeError as exc:
        _log.error("Claude returned non-JSON output: %s", exc)
        return _fallback_summary(emails)
    except Exception as exc:  # noqa: BLE001
        _log.error("summarize_emails failed: %s", exc)
        return _fallback_summary(emails)


def _fallback_summary(emails: list[dict[str, Any]]) -> EmailSummary:
    """Return a minimal summary when the LLM call fails."""
    items = [
        EmailItem(
            urgencia="media",
            resumen_breve=e.get("snippet", "(sin extracto)")[:120],
            accion_sugerida="Revisar el correo manualmente.",
        )
        for e in emails
    ]
    return EmailSummary(
        resumen_general=(
            f"Tienes {len(emails)} correo(s) no leído(s). "
            "No fue posible generar el resumen automático en este momento."
        ),
        total_no_leidos=len(emails),
        correos=items,
    )
