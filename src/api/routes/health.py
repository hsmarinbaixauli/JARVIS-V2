"""Health check endpoints.

GET /api/health  — lightweight liveness probe.
GET /api/health/detailed  — per-service status check (added in Step 13).
"""
from __future__ import annotations

import os
import sqlite3

from fastapi import APIRouter

router = APIRouter()


@router.get("/health")
async def health() -> dict:
    return {"status": "ok", "version": "2.0"}


@router.get("/health/detailed")
async def health_detailed() -> dict:
    from src.api.dependencies import get_services
    from src.persistence.database import _DB_PATH

    services: dict = {}

    # Anthropic — require non-empty API key
    api_key = os.environ.get("ANTHROPIC_API_KEY", "")
    services["anthropic"] = {
        "status": "ok" if api_key else "error",
        "detail": "" if api_key else "ANTHROPIC_API_KEY is not set",
    }

    # Google Calendar — check for credential env vars
    google_creds = os.environ.get("GOOGLE_CREDENTIALS", "") or os.environ.get("GOOGLE_TOKEN", "")
    services["google_calendar"] = {
        "status": "ok" if google_creds else "unconfigured",
    }

    # Gmail — same credential check
    services["gmail"] = {
        "status": "ok" if google_creds else "unconfigured",
    }

    # ERP — check live services dict
    try:
        svc = get_services()
        erp_client = svc.get("erp")
        services["erp"] = {"status": "ok" if erp_client is not None else "unconfigured"}
    except Exception as exc:
        services["erp"] = {"status": "error", "detail": str(exc)}

    # Database — try opening the SQLite file and run SELECT 1
    try:
        conn = sqlite3.connect(str(_DB_PATH), timeout=2)
        conn.execute("SELECT 1")
        conn.close()
        services["database"] = {"status": "ok"}
    except Exception as exc:
        services["database"] = {"status": "error", "detail": str(exc)}

    # Overall status: "degraded" if any configured service reports "error"
    overall = "ok"
    for svc_info in services.values():
        if svc_info.get("status") == "error":
            overall = "degraded"
            break

    return {"status": overall, "services": services}
