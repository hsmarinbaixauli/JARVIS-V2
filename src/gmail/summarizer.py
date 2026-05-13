"""Gmail email summarization using Claude. Provides summarize_emails(emails,
anthropic_client) which calls claude-haiku-4-5-20251001 with a Spanish-language
system prompt to produce a structured JSON digest of unread emails. Returns a
GmailSummary with resumen_general, total_no_leidos, and a list of EmailItem
records with urgencia, resumen_breve, and accion_sugerida fields."""
from __future__ import annotations


async def summarize_emails(emails: list, anthropic_client) -> dict:
    pass
