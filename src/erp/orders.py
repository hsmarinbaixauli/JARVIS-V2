"""Expande ERP order lookup.

get_order_status(client, order_id) navigates to the orders page, searches by
order ID inside the ERP iframe, scrapes the results table, and returns a
structured dict. Returns {'found': False, ...} when nothing matches.
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


async def get_order_status(client: ERPClient, order_id: str) -> dict[str, Any]:
    """Navigate to the orders page, search by order_id, and return structured results.

    Returns::

        {
            "found": bool,
            "order_id": str,
            "rows": list[dict]   # column-header -> cell-value for each result row
        }
    """
    async with client.get_page() as page:
        await page.goto(ORDERS_URL)
        await page.wait_for_load_state("networkidle")

        # Search controls live inside an iframe; use the first child frame when present.
        frame = page.frames[1] if len(page.frames) > 1 else page.main_frame

        await frame.wait_for_selector(ORDERS_SEARCH_INPUT)
        await frame.fill(ORDERS_SEARCH_INPUT, order_id)
        await frame.click(ORDERS_SEARCH_BUTTON)
        await frame.wait_for_load_state("networkidle")

        rows = await _extract_table(frame, ORDERS_RESULTS_TABLE)
        return {
            "found": len(rows) > 0,
            "order_id": order_id,
            "rows": rows,
        }


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
