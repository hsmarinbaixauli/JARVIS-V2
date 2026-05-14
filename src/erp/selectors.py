"""DOM selector constants for the Expande ERP (w3erp).

All values are derived from inspecting the live ERP with browser DevTools.
CSS selectors use the 'name' attribute where available for stability.
"""
from __future__ import annotations

# Login page URL
LOGIN_URL: str = "https://afosxsofa.expande.es/ERP/3.2/inicio/w3erp/index.php"

# Login form selectors
LOGIN_NICK: str = 'input[name="nick"]'
LOGIN_USER: str = 'input[name="login"]'
LOGIN_PASS: str = 'input[name="passwd"]'
LOGIN_SUBMIT: str = 'button[type="submit"]'

# Post-login success indicators
DASHBOARD_URL_FRAGMENT: str = "/base/php/pag/u/"
DASHBOARD_TITLE_FRAGMENT: str = "Escritorio"

# Orders page URL
ORDERS_URL: str = "https://afosxsofa.expande.es/ERP/3.2/base/php/pag/u/u09004000.php"

# Orders page selectors — these live inside an iframe
ORDERS_SEARCH_INPUT: str = 'input[name="compo_pers"]'
ORDERS_SEARCH_BUTTON: str = "button"   # first button in the iframe
ORDERS_RESULTS_TABLE: str = "table"    # results table in the iframe
