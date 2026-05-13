"""ERPClient: manages a single persistent Playwright Chromium browser instance
and BrowserContext. Provides async context manager get_page() that acquires an
asyncio.Lock to serialize ERP calls. Handles session expiry detection (redirect
back to login page) and automatic re-login. Initialized at FastAPI startup via
lifespan."""
from __future__ import annotations


class ERPClient:
    pass
