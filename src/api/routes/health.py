"""Health check endpoints. GET /api/health returns lightweight liveness status.
GET /api/health/detailed checks all downstream services (Anthropic, Google OAuth,
ERP session, SQLite) and returns per-service status."""
from __future__ import annotations
