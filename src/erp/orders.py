"""Expande ERP order lookup. Provides get_order_status(client, order_id) which
navigates to the order detail page, scrapes order header fields (status,
customer, date, total) and line items table, and returns a structured dict.
Returns {'found': False, 'order_id': order_id} if the order does not exist."""
from __future__ import annotations


async def get_order_status(client, order_id: str) -> dict:
    pass
