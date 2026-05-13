"""Expande ERP customer search. Provides search_by_customer(client,
customer_name, max_results=10) which navigates to the search section, enters
the customer name, submits, scrapes the results table, and returns a list of
order summary dicts."""
from __future__ import annotations


async def search_by_customer(client, customer_name: str, max_results: int = 10) -> list:
    pass
