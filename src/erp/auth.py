"""Expande ERP login flow using Playwright.

login(page) navigates to the ERP login page, fills the three login fields
(Nick, Username, Password) from environment variables, submits the form, and
verifies success by checking the post-login URL and page title.
"""
from __future__ import annotations

import logging
import os

from playwright.async_api import Page

from src.erp.selectors import (
    DASHBOARD_TITLE_FRAGMENT,
    DASHBOARD_URL_FRAGMENT,
    LOGIN_NICK,
    LOGIN_PASS,
    LOGIN_SUBMIT,
    LOGIN_URL,
    LOGIN_USER,
)

_log = logging.getLogger(__name__)
_TIMEOUT = int(os.getenv("ERP_TIMEOUT_MS", "15000"))


class ERPLoginError(Exception):
    pass


async def login(page: Page) -> None:
    """Log in to the Expande ERP. Raises ERPLoginError on failure."""
    nick = os.getenv("ERP_NICK", "")
    user = os.getenv("ERP_USER", "")
    password = os.getenv("ERP_PASS", "")

    if not all([nick, user, password]):
        raise ERPLoginError(
            "ERP credentials not set — ensure ERP_NICK, ERP_USER, and ERP_PASS are in .env"
        )

    _log.info("Navigating to ERP login page")
    await page.goto(LOGIN_URL, timeout=_TIMEOUT)

    await page.fill(LOGIN_NICK, nick, timeout=_TIMEOUT)
    await page.fill(LOGIN_USER, user, timeout=_TIMEOUT)
    await page.fill(LOGIN_PASS, password, timeout=_TIMEOUT)
    await page.click(LOGIN_SUBMIT, timeout=_TIMEOUT)

    # Wait for navigation to an authenticated page
    await page.wait_for_url(f"**{DASHBOARD_URL_FRAGMENT}**", timeout=_TIMEOUT)

    title = await page.title()
    if DASHBOARD_TITLE_FRAGMENT not in title:
        raise ERPLoginError(
            f"Login appeared to succeed (URL ok) but page title is unexpected: {title!r}"
        )

    _log.info("ERP login successful")


def is_logged_in_url(url: str) -> bool:
    """Return True if the URL looks like an authenticated ERP page."""
    return DASHBOARD_URL_FRAGMENT in url
