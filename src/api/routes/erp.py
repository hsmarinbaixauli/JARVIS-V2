"""Expande ERP endpoints.

GET /api/erp/order/{order_id}  — look up a specific order by ID.
GET /api/erp/search?customer=  — search orders by customer name.

Both endpoints require the ERP Playwright client to be initialised at startup
(ERP_NICK, ERP_USER, ERP_PASS must be set). Returns HTTP 503 when the client
is not available rather than crashing.
"""
from __future__ import annotations

import logging

from fastapi import APIRouter, Depends, HTTPException, Query, status

from src.api.dependencies import get_services

_log = logging.getLogger(__name__)
router = APIRouter()


@router.get("/erp/order/{order_id}")
async def erp_get_order(
    order_id: str,
    services: dict = Depends(get_services),
) -> dict:
    """Look up an ERP order by ID. Returns structured row data from the ERP table."""
    erp = services.get("erp")
    if erp is None:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="ERP client not initialised. Check ERP_NICK, ERP_USER, ERP_PASS in .env.",
        )
    try:
        from src.erp.orders import get_order_status
        return await get_order_status(erp, order_id)
    except Exception as exc:
        _log.error("ERP order lookup failed for %r: %s", order_id, exc)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"ERP lookup failed: {exc}",
        ) from exc


@router.get("/erp/search")
async def erp_search(
    customer: str = Query(..., description="Customer name to search for"),
    max_results: int = Query(default=10, ge=1, le=50),
    services: dict = Depends(get_services),
) -> list:
    """Search ERP orders by customer name."""
    erp = services.get("erp")
    if erp is None:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="ERP client not initialised. Check ERP_NICK, ERP_USER, ERP_PASS in .env.",
        )
    try:
        from src.erp.search import search_by_customer
        return await search_by_customer(erp, customer, max_results=max_results)
    except Exception as exc:
        _log.error("ERP search failed for customer %r: %s", customer, exc)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"ERP search failed: {exc}",
        ) from exc
