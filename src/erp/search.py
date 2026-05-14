"""Expande ERP customer search.

search_by_customer(client, customer_name, max_results=10) navigates to the
orders page, enters the customer name in the iframe search field, submits,
scrapes the results table, and returns a list of order summary dicts capped at
max_results.
"""
from __future__ import annotations

import logging
from typing import Any

from src.erp.client import ERPClient
from src.erp.selectors import (
    ORDERS_RESULTS_TABLE,
    ORDERS_SEARCH_BUTTON,
    ORDERS_SEARCH_INPUT,
    ORDERS_URL,
)

_log = logging.getLogger(__name__)


async def search_by_customer(
    client: ERPClient,
    customer_name: str,
    max_results: int = 10,
) -> list[dict[str, Any]]:
    """Search orders by customer name. Returns up to max_results rows."""
    async with client.get_page() as page:
        await page.goto(ORDERS_URL)
        await page.wait_for_load_state("networkidle")

        frame = page.frames[1] if len(page.frames) > 1 else page.main_frame

        await frame.wait_for_selector(ORDERS_SEARCH_INPUT)
        await frame.fill(ORDERS_SEARCH_INPUT, customer_name)
        await frame.click(ORDERS_SEARCH_BUTTON)
        await frame.wait_for_load_state("networkidle")

        rows = await _extract_table(frame, ORDERS_RESULTS_TABLE)
        return rows[:max_results]


async def _extract_table(frame: Any, selector: str) -> list[dict[str, str]]:
    """Extract an HTML table from frame into a list of row dicts."""
    table = await frame.query_selector(selector)
    if table is None:
        return []

    headers = [
        (await h.inner_text()).strip()
        for h in await table.query_selector_all("th")
    ]

    rows: list[dict[str, str]] = []
    for tr in await table.query_selector_all("tr"):
        cells = [
            (await td.inner_text()).strip()
            for td in await tr.query_selector_all("td")
        ]
        if not cells:
            continue
        if headers and len(cells) == len(headers):
            rows.append(dict(zip(headers, cells)))
        else:
            rows.append({str(i): v for i, v in enumerate(cells)})
    return rows
