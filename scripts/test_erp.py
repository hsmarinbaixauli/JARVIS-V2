"""Standalone ERP diagnostic script — Playwright sync API, headed mode.

Confirmed approach:
  - Frame name="u09004000B" contains the search form.
  - Visible pedido field: input[name="t1_bjj0010"] — fill with force=True.
  - f_t1_bjj0010 is the hidden mirror; do not target it directly.
  - Submit by pressing Enter in the visible field.
  - Results table appears in the same frame after ~3 s.

Run:
    python scripts/test_erp.py
"""
from __future__ import annotations

import os
import sys
import time

_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, _ROOT)

try:
    from dotenv import load_dotenv
    load_dotenv(os.path.join(_ROOT, ".env"))
except ImportError:
    print("[warn] python-dotenv not installed — reading env vars from shell only")

from playwright.sync_api import sync_playwright

# ── Config ────────────────────────────────────────────────────────────────────

LOGIN_URL  = os.getenv("ERP_URL", "https://afosxsofa.expande.es/ERP/3.2/inicio/w3erp/index.php")
NICK       = os.getenv("ERP_NICK", "")
USER       = os.getenv("ERP_USER", "")
PASSWORD   = os.getenv("ERP_PASS", "")
ORDERS_URL = (
    "https://afosxsofa.expande.es/ERP/3.2/base/php/pag/u/u09004000.php"
    "?raiz=&pagina=https://afosxsofa.expande.es/ERP/3.2/base/php/pag/u/u09004000.php"
    "&activa_frame_oculto=S&ventanas=S&dir_prog="
    "&componente=p01104001&tabla=t00010120&clave_939=&permisos=SNSSSSSSSS"
)

SEARCH_FRAME_NAME = "u09004000B"
SEARCH_INPUT      = 'input[name="f_t1_bjj0030"]'  # visible "Pedido" field (confirmed)
ORDER_ID          = "6886"
TIMEOUT           = 15_000
FRAME_DEADLINE    = 15   # seconds to wait for frame to leave about:blank


# ── Helpers ───────────────────────────────────────────────────────────────────

def sep(title: str = "") -> None:
    print("\n" + "─" * 60)
    if title:
        print(f"  {title}")
        print("─" * 60)


def dump_frames(page, label: str) -> None:
    frames = page.frames
    sep(f"Frames — {label}  ({len(frames)} total)")
    for i, f in enumerate(frames):
        try:
            inputs = f.query_selector_all("input")
            names  = [inp.get_attribute("name") or "(no name)" for inp in inputs]
        except Exception as exc:
            names = [f"ERROR: {exc}"]
        print(f"  [{i}] name={f.name!r:20s}  url={f.url!r}")
        if names:
            print(f"        inputs ({len(names)}): {names}")


def wait_for_frame(page, name: str, deadline_s: int = FRAME_DEADLINE):
    """Poll until the named frame exists and its URL is not about:blank."""
    deadline = time.time() + deadline_s
    while time.time() < deadline:
        f = next((f for f in page.frames if f.name == name), None)
        url = f.url if f else "not found"
        print(f"  ... frame={name!r}  url={url!r}")
        if f is not None and url not in ("about:blank", ""):
            return f
        time.sleep(0.5)
    return None


# ── Main ──────────────────────────────────────────────────────────────────────

def main() -> None:
    if not all([NICK, USER, PASSWORD]):
        print("ERROR: ERP_NICK, ERP_USER, ERP_PASS must be set in .env")
        sys.exit(1)

    with sync_playwright() as pw:
        browser = pw.chromium.launch(headless=False, slow_mo=200)
        ctx     = browser.new_context()
        page    = ctx.new_page()

        # ── Step 1: Login ──────────────────────────────────────────────────────
        sep("Step 1 — Login")
        page.goto(LOGIN_URL, timeout=TIMEOUT)
        page.wait_for_load_state("domcontentloaded", timeout=TIMEOUT)
        page.fill('input[name="nick"]',   NICK,     timeout=TIMEOUT)
        page.fill('input[name="login"]',  USER,     timeout=TIMEOUT)
        page.fill('input[name="passwd"]', PASSWORD, timeout=TIMEOUT)
        page.click('button[type="submit"]', timeout=TIMEOUT)
        page.wait_for_url("**/base/php/pag/u/**", timeout=TIMEOUT)
        print(f"  ✓ Logged in — url={page.url!r}")

        # ── Step 2: Navigate to orders URL ────────────────────────────────────
        sep("Step 2 — Navigate to orders URL")
        page.goto(ORDERS_URL, timeout=TIMEOUT)
        page.wait_for_load_state("domcontentloaded", timeout=TIMEOUT)
        print(f"  Landed — url={page.url!r}  title={page.title()!r}")

        # ── Step 3: Poll for frame "u09004000B" ───────────────────────────────
        sep(f"Step 3 — Wait for frame name={SEARCH_FRAME_NAME!r}")
        search_frame = wait_for_frame(page, SEARCH_FRAME_NAME)

        dump_frames(page, f"after frame wait (target url={search_frame.url if search_frame else 'n/a'})")

        if search_frame is None:
            print(f"  ✗ Frame {SEARCH_FRAME_NAME!r} never loaded")
            browser.close()
            return
        print(f"  ✓ Frame ready — url={search_frame.url!r}")

        # ── Step 4: Fill visible pedido field with force=True ─────────────────
        sep(f"Step 4 — Fill {SEARCH_INPUT!r} with {ORDER_ID!r} (force=True)")
        try:
            search_frame.locator(SEARCH_INPUT).fill(ORDER_ID, force=True)
            print(f"  ✓ Filled")
        except Exception as exc:
            print(f"  ✗ fill failed: {exc}")
            print("  Inputs in frame:")
            for inp in search_frame.query_selector_all("input"):
                print(f"    name={inp.get_attribute('name')!r}  "
                      f"type={inp.get_attribute('type')!r}  "
                      f"visible={inp.is_visible()}")
            browser.close()
            return

        # ── Step 5: Press Enter to submit ─────────────────────────────────────
        sep("Step 5 — Press Enter")
        search_frame.locator(SEARCH_INPUT).press("Enter")
        print("  ✓ Enter pressed")

        # ── Step 6: Wait 3 s for results ──────────────────────────────────────
        sep("Step 6 — Wait 3 s for results")
        time.sleep(3)

        # ── Step 7: Print tables ───────────────────────────────────────────────
        sep("Step 7 — Tables in frame after submit")
        tables = search_frame.query_selector_all("table")
        print(f"  {len(tables)} table(s) found")
        for i, tbl in enumerate(tables):
            txt = tbl.inner_text().strip()
            print(f"\n  Table [{i}] ({len(txt)} chars):\n{txt[:2000]}")

        sep("Step 8 — Raw frame body HTML (first 3000 chars)")
        try:
            print(search_frame.inner_html("body")[:3000])
        except Exception as exc:
            print(f"  ERROR: {exc}")
            print(page.content()[:3000])

        sep("Done — browser stays open 10 s")
        time.sleep(10)
        browser.close()


if __name__ == "__main__":
    main()
