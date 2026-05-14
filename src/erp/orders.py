"""Expande ERP order lookup.

Confirmed structure (scripts/test_erp.py):
  - Search form is in the frame named "u09004000B".
  - Pedido (order number) field: input[name="f_t1_bjj0030"] — fill with force=True.
  - Submit by pressing Enter in that field.
  - Results appear in Table [2] (0-indexed) of the same frame after ~3 s.
  - Result columns: Cliente, Nombre, Estado Cliente, Serie, Pedido,
                    Fecha pedido, Estado Pedido, Su referencia, Su fecha,
                    B.Imponible, Ult. avance
"""
from __future__ import annotations

import asyncio
import logging
import time as _time
from typing import Any

from src.erp.client import ERPClient
from src.erp.selectors import (
    ORDERS_RESULTS_COLUMNS,
    ORDERS_RESULTS_TABLE_INDEX,
    ORDERS_SEARCH_FRAME_NAME,
    ORDERS_SEARCH_INPUT,
    ORDERS_URL,
)

_log = logging.getLogger(__name__)

_TIMEOUT = 15_000          # ms — Playwright timeouts
_FRAME_POLL_INTERVAL = 0.5 # s
_FRAME_POLL_DEADLINE = 15  # s


async def get_order_status(client: ERPClient, order_id: str) -> dict[str, Any]:
    """Search for order_id in the Expande ERP and return structured results.

    Flow:
      1. Navigate to ORDERS_URL (PHPSESSID cookie handles auth automatically).
      2. Poll until frame "u09004000B" appears with a non-blank URL.
      3. Fill input[name="f_t1_bjj0030"] with order_id (force=True).
      4. Press Enter to submit.
      5. Wait 3 s, then extract Table [2] from the frame.

    Returns::

        {
            "found": bool,
            "order_id": str,
            "rows": list[dict]  # keys match ORDERS_RESULTS_COLUMNS
        }
    """
    async with client.get_page() as page:
        _log.debug("get_order_status(%r): navigating to orders URL", order_id)
        await page.goto(ORDERS_URL, timeout=_TIMEOUT)
        await page.wait_for_load_state("domcontentloaded", timeout=_TIMEOUT)
        _log.debug("get_order_status(%r): landed url=%r title=%r",
                   order_id, page.url, await page.title())

        frame = await wait_for_search_frame(page, order_id)
        if frame is None:
            raise RuntimeError(
                f"Frame {ORDERS_SEARCH_FRAME_NAME!r} never loaded. "
                "Frames: " + str([(f.name, f.url) for f in page.frames])
            )
        _log.debug("get_order_status(%r): frame ready url=%r", order_id, frame.url)

        _log.debug("get_order_status(%r): filling %r with %r (force=True)",
                   order_id, ORDERS_SEARCH_INPUT, order_id)
        await frame.locator(ORDERS_SEARCH_INPUT).fill(order_id, force=True)
        await frame.locator(ORDERS_SEARCH_INPUT).press("Enter")

        _log.debug("get_order_status(%r): waiting 3 s for results", order_id)
        await asyncio.sleep(3)

        rows = await extract_results_table(frame, label=order_id)
        _log.debug("get_order_status(%r): extracted %d row(s)", order_id, len(rows))
        return {
            "found": len(rows) > 0,
            "order_id": order_id,
            "rows": rows,
        }


# ── Shared helpers (imported by search.py) ────────────────────────────────────

async def wait_for_search_frame(page: Any, label: str) -> Any | None:
    """Poll until the "u09004000B" frame exists and its URL is not about:blank."""
    deadline = _time.monotonic() + _FRAME_POLL_DEADLINE
    while _time.monotonic() < deadline:
        frame = next((f for f in page.frames if f.name == ORDERS_SEARCH_FRAME_NAME), None)
        url = frame.url if frame else "not found"
        if frame is not None and url not in ("about:blank", ""):
            _log.debug("wait_for_search_frame(%r): frame loaded url=%r", label, url)
            return frame
        _log.debug("wait_for_search_frame(%r): waiting — url=%r", label, url)
        await asyncio.sleep(_FRAME_POLL_INTERVAL)
    return None


async def extract_results_table(frame: Any, label: str = "") -> list[dict[str, str]]:
    """Extract Table [ORDERS_RESULTS_TABLE_INDEX] from the search frame.

    Falls back to the last table if the indexed one does not exist.
    Uses ORDERS_RESULTS_COLUMNS as header names when the table has no <th> row.
    """
    all_tables = await frame.query_selector_all("table")
    _log.debug("extract_results_table(%r): %d table(s) found", label, len(all_tables))
    if not all_tables:
        return []

    idx = ORDERS_RESULTS_TABLE_INDEX
    table = all_tables[idx] if idx < len(all_tables) else all_tables[-1]
    _log.debug("extract_results_table(%r): using table index %d", label,
               idx if idx < len(all_tables) else len(all_tables) - 1)

    # Try <th> headers first; fall back to the confirmed column list.
    th_els = await table.query_selector_all("th")
    if th_els:
        headers = [(await h.inner_text()).strip() for h in th_els]
    else:
        headers = list(ORDERS_RESULTS_COLUMNS)

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
            # Partial row — map by position, pad missing columns with ""
            row: dict[str, str] = {}
            for i, col in enumerate(headers):
                row[col] = cells[i] if i < len(cells) else ""
            rows.append(row)

    return rows
