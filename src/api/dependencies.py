"""FastAPI dependency injection providers. Supplies initialized service clients
(Anthropic, Google Calendar, Gmail, Playwright ERPClient, SQLite repository) to
route handlers via Depends()."""
from __future__ import annotations
