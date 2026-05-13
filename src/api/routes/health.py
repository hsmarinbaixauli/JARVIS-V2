"""Health check endpoints.

GET /api/health  — lightweight liveness probe.
GET /api/health/detailed  — per-service status check (added in Step 13).
"""
from __future__ import annotations

from fastapi import APIRouter

router = APIRouter()


@router.get("/health")
async def health() -> dict:
    return {"status": "ok", "version": "2.0"}
