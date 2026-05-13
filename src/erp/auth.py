"""Expande ERP login flow using Playwright. Provides login(page) which
navigates to ERP_URL, fills the three login fields (Nick, Username, Password)
from environment variables using selectors from selectors.py, submits the
form, and verifies successful login by checking for the dashboard indicator
element."""
from __future__ import annotations


async def login(page) -> None:
    pass
