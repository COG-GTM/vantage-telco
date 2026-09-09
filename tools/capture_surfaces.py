"""Drive the visible Chrome (CDP :29229) through the modernization capture surfaces.

Usage: python tools/capture_surfaces.py <out_dir> <prefix>
Writes <prefix>-dashboard.png, <prefix>-dashboard-billing.png, <prefix>-capacity.png,
<prefix>-swagger.png as full-page screenshots.
"""

from __future__ import annotations

import sys
import time
from pathlib import Path

from playwright.sync_api import sync_playwright

BASE = "http://localhost:8000"


def scroll_through(page) -> None:
    height = page.evaluate("document.body.scrollHeight")
    y = 0
    while y < height:
        y += 600
        page.evaluate(f"window.scrollTo(0, {y})")
        time.sleep(0.35)
    time.sleep(0.5)
    page.evaluate("window.scrollTo(0, 0)")
    time.sleep(0.4)


def main(out_dir: str, prefix: str) -> None:
    out = Path(out_dir)
    out.mkdir(parents=True, exist_ok=True)
    with sync_playwright() as p:
        browser = p.chromium.connect_over_cdp("http://localhost:29229")
        ctx = browser.contexts[0]
        page = ctx.pages[0] if ctx.pages else ctx.new_page()
        page.bring_to_front()

        page.goto(f"{BASE}/dashboard", wait_until="networkidle")
        time.sleep(1.5)
        scroll_through(page)
        page.screenshot(path=str(out / f"{prefix}-dashboard.png"), full_page=True)

        page.goto(f"{BASE}/dashboard/billing", wait_until="networkidle")
        time.sleep(1.5)
        scroll_through(page)
        page.goto(f"{BASE}/dashboard/billing?period=2026-07", wait_until="networkidle")
        time.sleep(1.5)
        scroll_through(page)
        page.screenshot(path=str(out / f"{prefix}-dashboard-billing.png"), full_page=True)

        page.goto(f"{BASE}/capacity", wait_until="networkidle")
        time.sleep(1.5)
        page.locator("#search").fill("RIV-01")
        time.sleep(1.5)
        page.locator("#requested").fill("100")
        time.sleep(2)
        page.locator("#requested").fill("100000")
        time.sleep(2)
        scroll_through(page)
        page.screenshot(path=str(out / f"{prefix}-capacity.png"), full_page=True)

        page.goto(f"{BASE}/docs", wait_until="networkidle")
        time.sleep(2)
        op = page.locator("#operations-billing-get_invoices_billing_invoices_get").first
        if op.count() == 0:
            op = page.locator(".opblock", has_text="/billing/invoices").first
        op.locator(".opblock-summary").click()
        time.sleep(1)
        page.get_by_role("button", name="Try it out").click()
        time.sleep(0.5)
        period = op.locator("input[placeholder='period']")
        if period.count() == 0:
            period = op.locator("tr", has_text="period").locator("input").first
        period.fill("2026-07")
        page.get_by_role("button", name="Execute").click()
        time.sleep(3)
        scroll_through(page)
        page.screenshot(path=str(out / f"{prefix}-swagger.png"), full_page=True)
        page.evaluate("window.scrollTo(0, 0)")
        time.sleep(1)


if __name__ == "__main__":
    main(sys.argv[1], sys.argv[2])
