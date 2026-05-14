"""Expande ERP customer search.

search_by_customer(client, customer_name, max_results=10) navigates to the
orders page, enters the customer name in the Nombre field, submits, and returns
a list of matching order rows capped at max_results.

Confirmed structure (scripts/test_erp.py):
  - Search form is in the frame named "u09004000B".
  - Nombre cliente field: input[name="f_t2_bva0020"] — fill with force=True.
  - Submit by pressing Enter in that field.
  - Results appear in Table [2] of the same frame after ~3 s.
"""
from __future__ import annotations

import asyncio
import logging
from typing import Any

from src.erp.client import ERPClient
from src.erp.orders import extract_results_table, wait_for_search_frame
from src.erp.selectors import (
    ORDERS_SEARCH_NOMBRE,
    ORDERS_URL,
)

_log = logging.getLogger(__name__)

_TIMEOUT = 15_000  # ms


async def search_by_customer(
    client: ERPClient,
    customer_name: str,
    max_results: int = 10,
) -> list[dict[str, Any]]:
    """Search ERP orders by customer name and return up to max_results rows.

    Each row is a dict with keys matching ORDERS_RESULTS_COLUMNS:
      Cliente, Nombre, Estado Cliente, Serie, Pedido, Fecha pedido,
      Estado Pedido, Su referencia, Su fecha, B.Imponible, Ult. avance
    """
    async with client.get_page() as page:
        _log.debug("search_by_customer(%r): navigating to orders URL", customer_name)
        await page.goto(ORDERS_URL, timeout=_TIMEOUT)
        await page.wait_for_load_state("domcontentloaded", timeout=_TIMEOUT)
        _log.debug("search_by_customer(%r): landed url=%r title=%r",
                   customer_name, page.url, await page.title())

        frame = await wait_for_search_frame(page, customer_name)
        if frame is None:
            raise RuntimeError(
                f"Orders search frame never loaded for customer search {customer_name!r}. "
                "Frames: " + str([(f.name, f.url) for f in page.frames])
            )
        _log.debug("search_by_customer(%r): frame ready url=%r", customer_name, frame.url)

        _log.debug("search_by_customer(%r): filling Nombre field %r (force=True)",
                   customer_name, ORDERS_SEARCH_NOMBRE)
        await frame.locator(ORDERS_SEARCH_NOMBRE).fill(customer_name, force=True)
        await frame.locator(ORDERS_SEARCH_NOMBRE).press("Enter")

        _log.debug("search_by_customer(%r): waiting 3 s for results", customer_name)
        await asyncio.sleep(3)

        rows = await extract_results_table(frame, label=customer_name)
        _log.debug("search_by_customer(%r): extracted %d row(s), capping at %d",
                   customer_name, len(rows), max_results)
        return rows[:max_results]
