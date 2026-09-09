"""Record the three human-review surfaces of the running app.

Usage:
    python docs/modernization/capture.py <out_dir> <prefix> [--base-url http://localhost:8000]

Writes, into <out_dir>:
    <prefix>-dashboard.png          full-page screenshot of /dashboard
    <prefix>-dashboard-billing.png  full-page screenshot of /dashboard/billing
    <prefix>-capacity.png           full-page screenshot of /capacity (after a quote)
    <prefix>-walkthrough.webm       one video visiting all three surfaces
    <prefix>-api.txt                curl-style dump of the JSON endpoints

Requires `pip install playwright && playwright install chromium`.
"""

from __future__ import annotations

import argparse
import json
import shutil
from pathlib import Path
from urllib.request import urlopen

from playwright.sync_api import sync_playwright

API_PATHS = [
    "/health",
    "/resources?limit=3",
    "/circuits",
    "/network/addressing",
    "/billing/invoices?period=2026-07",
    "/capacity/locations?requested_mbps=350",
]


def dump_api(base_url: str, out: Path) -> None:
    chunks = []
    for path in API_PATHS:
        with urlopen(base_url + path) as resp:  # noqa: S310 - local dev server
            body = resp.read().decode()
            status = resp.status
        try:
            body = json.dumps(json.loads(body), indent=2)
        except ValueError:
            pass
        if len(body) > 4000:
            body = body[:4000] + "\n... (truncated)"
        chunks.append(f"$ curl -s {base_url}{path}\nHTTP {status}\n{body}\n")
    out.write_text("\n".join(chunks))


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("out_dir")
    ap.add_argument("prefix")
    ap.add_argument("--base-url", default="http://localhost:8000")
    args = ap.parse_args()

    out = Path(args.out_dir)
    out.mkdir(parents=True, exist_ok=True)
    base = args.base_url.rstrip("/")

    dump_api(base, out / f"{args.prefix}-api.txt")

    with sync_playwright() as pw:
        browser = pw.chromium.launch()
        ctx = browser.new_context(
            viewport={"width": 1400, "height": 900},
            record_video_dir=str(out / "_video"),
            record_video_size={"width": 1400, "height": 900},
        )
        page = ctx.new_page()

        page.goto(f"{base}/dashboard", wait_until="networkidle")
        page.wait_for_timeout(1500)
        page.screenshot(path=str(out / f"{args.prefix}-dashboard.png"), full_page=True)

        page.goto(f"{base}/dashboard/billing?period=2026-07", wait_until="networkidle")
        page.wait_for_timeout(1500)
        page.mouse.wheel(0, 800)
        page.wait_for_timeout(800)
        page.screenshot(path=str(out / f"{args.prefix}-dashboard-billing.png"), full_page=True)

        page.goto(f"{base}/capacity", wait_until="networkidle")
        page.wait_for_timeout(1000)
        page.fill("#requested", "500")
        page.fill("#search", "Riverside")
        page.wait_for_timeout(1500)
        page.screenshot(path=str(out / f"{args.prefix}-capacity.png"), full_page=True)

        page.wait_for_timeout(800)
        video = page.video
        ctx.close()
        if video is not None:
            video.save_as(str(out / f"{args.prefix}-walkthrough.webm"))
        browser.close()
    shutil.rmtree(out / "_video", ignore_errors=True)


if __name__ == "__main__":
    main()
