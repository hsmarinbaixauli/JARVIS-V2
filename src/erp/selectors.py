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

# Dashboard — starting point for ERP navigation
DASHBOARD_URL: str = "https://afosxsofa.expande.es/ERP/3.2/base/php/pag/u/u09000001.php"

# Orders page — full URL with session parameters.
# PHPSESSID auth is carried by the BrowserContext cookie automatically after login.
ORDERS_URL: str = (
    "https://afosxsofa.expande.es/ERP/3.2/base/php/pag/u/u09004000.php"
    "?raiz=&pagina=https://afosxsofa.expande.es/ERP/3.2/base/php/pag/u/u09004000.php"
    "&activa_frame_oculto=S&ventanas=S&dir_prog="
    "&componente=p01104001&tabla=t00010120&clave_939=&permisos=SNSSSSSSSS"
)

# Orders search form — confirmed from live DOM inspection (scripts/test_erp.py).
# The search form lives in the frame named "u09004000B".
ORDERS_SEARCH_FRAME_NAME: str = "u09004000B"

# Search filter fields — all confirmed from 61-input frame scan.
# Use force=True when filling; some fields have CSS that hides them from Playwright.
ORDERS_SEARCH_INPUT: str = 'input[name="f_t1_bjj0030"]'   # Pedido (order number)
ORDERS_SEARCH_CLIENTE: str = 'input[name="f_t1_bjj0050"]' # Cliente (customer ID)
ORDERS_SEARCH_NOMBRE: str = 'input[name="f_t2_bva0020"]'  # Nombre cliente (customer name)
ORDERS_SEARCH_ESTADO: str = 'input[name="f_t4_bst0030"]'  # Estado Pedido (order status)

# Results: the results grid is Table [2] (0-indexed) inside the same frame.
# Column order confirmed from live inspection:
ORDERS_RESULTS_TABLE_INDEX: int = 2
ORDERS_RESULTS_COLUMNS: tuple[str, ...] = (
    "Cliente",
    "Nombre",
    "Estado Cliente",
    "Serie",
    "Pedido",
    "Fecha pedido",
    "Estado Pedido",
    "Su referencia",
    "Su fecha",
    "B.Imponible",
    "Ult. avance",
)
