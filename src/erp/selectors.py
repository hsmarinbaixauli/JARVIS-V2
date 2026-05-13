"""DOM selector constants for the Expande ERP (w3erp). All selector values are
empty strings and must be filled by inspecting the live ERP at ERP_URL with
browser DevTools. Prefer CSS selectors using the 'name' attribute (e.g.
input[name='nick']) over class-based selectors for stability."""
from __future__ import annotations

# Login form selectors
LOGIN_NICK: str = ""
LOGIN_USER: str = ""
LOGIN_PASS: str = ""
LOGIN_SUBMIT: str = ""
DASHBOARD_INDICATOR: str = ""

# Order detail selectors
ORDER_SEARCH_INPUT: str = ""
ORDER_STATUS_FIELD: str = ""
ORDER_CUSTOMER_FIELD: str = ""
ORDER_DATE_FIELD: str = ""
ORDER_TOTAL_FIELD: str = ""
ORDER_LINES_TABLE: str = ""

# Customer search selectors
SEARCH_NAV_LINK: str = ""
SEARCH_CUSTOMER_INPUT: str = ""
SEARCH_SUBMIT_BTN: str = ""
SEARCH_RESULTS_TABLE: str = ""
SEARCH_RESULTS_ROW: str = ""

# Search results column indices
SEARCH_COL_ORDER_ID: int = 0
SEARCH_COL_CUSTOMER: int = 1
SEARCH_COL_STATUS: int = 2
SEARCH_COL_DATE: int = 3
