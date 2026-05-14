"""ERPClient: manages a single persistent Playwright Chromium browser instance.

Provides async context manager get_page() that acquires an asyncio.Lock to
serialise ERP calls. Handles session-expiry detection (redirect back to the
login page) and automatic re-login. Initialised at FastAPI startup via the
lifespan hook in app.py and shut down on exit.
"""
from __future__ import annotations

import asyncio
import logging
import os
import sys
from contextlib import asynccontextmanager
from typing import AsyncGenerator

from playwright.async_api import Browser, BrowserContext, Page, async_playwright

from src.erp.auth import ERPLoginError, is_logged_in_url, login
from src.erp.selectors import DASHBOARD_URL_FRAGMENT, LOGIN_URL

_log = logging.getLogger(__name__)
_TIMEOUT = int(os.getenv("ERP_TIMEOUT_MS", "15000"))


class ERPClient:
    """Single persistent Chromium session for the Expande ERP.

    Usage::

        client = ERPClient()
        await client.start()          # launches browser, logs in
        async with client.get_page() as page:
            ...                       # serialised ERP interaction
        await client.stop()           # clean shutdown
    """

    def __init__(self) -> None:
        self._lock = asyncio.Lock()
        self._playwright = None
        self._browser: Browser | None = None
        self._context: BrowserContext | None = None
        self._page: Page | None = None
        self._loop: asyncio.AbstractEventLoop | None = None

    async def start(self) -> None:
        """Launch Chromium and log in to the ERP."""
        self._loop = asyncio.get_event_loop()
        if sys.platform == "win32" and not isinstance(self._loop, asyncio.ProactorEventLoop):
            logging.getLogger(__name__).warning(
                "ERP: running on Windows without ProactorEventLoop — "
                "subprocess support may be missing. Ensure app.py sets "
                "WindowsProactorEventLoopPolicy before uvicorn starts."
            )
        self._playwright = await async_playwright().start()
        self._browser = await self._playwright.chromium.launch(headless=True)
        self._context = await self._browser.new_context()
        self._page = await self._context.new_page()
        await login(self._page)

    def run_sync(self, coro, timeout: float = 30.0):
        """Schedule a coroutine on the main event loop from a worker thread.

        Playwright objects are bound to the event loop they were created in.
        When dispatch() runs inside asyncio.to_thread() there is no running loop
        in that thread, so asyncio.run() would create a foreign loop and crash.
        This method safely bridges the gap using run_coroutine_threadsafe.
        """
        if self._loop is None:
            raise ERPLoginError("ERPClient has not been started — call start() first")
        future = asyncio.run_coroutine_threadsafe(coro, self._loop)
        return future.result(timeout=timeout)

    async def stop(self) -> None:
        """Close the browser and stop Playwright."""
        if self._page:
            await self._page.close()
        if self._context:
            await self._context.close()
        if self._browser:
            await self._browser.close()
        if self._playwright:
            await self._playwright.stop()
        self._page = self._context = self._browser = self._playwright = None

    @asynccontextmanager
    async def get_page(self) -> AsyncGenerator[Page, None]:
        """Yield the shared Page, serialised by asyncio.Lock.

        Automatically re-logs in if the session has expired (detected by the
        current URL being on the login page).
        """
        async with self._lock:
            if self._page is None:
                raise ERPLoginError("ERPClient has not been started — call start() first")

            current_url = self._page.url or ""
            # If the page has been redirected back to the login URL, re-authenticate.
            if current_url and LOGIN_URL in current_url and DASHBOARD_URL_FRAGMENT not in current_url:
                _log.warning("ERP session appears expired — re-logging in")
                await login(self._page)

            yield self._page


# ---------------------------------------------------------------------------
# Module-level singleton — managed by app.py lifespan
# ---------------------------------------------------------------------------

_client: ERPClient | None = None


def get_erp_client() -> ERPClient | None:
    """Return the active module-level ERPClient, or None if not initialised."""
    return _client


async def init_erp_client() -> ERPClient:
    """Create, start, and cache the module-level ERPClient."""
    global _client
    _client = ERPClient()
    await _client.start()
    return _client


async def shutdown_erp_client() -> None:
    """Stop and clear the module-level ERPClient."""
    global _client
    if _client is not None:
        await _client.stop()
        _client = None
