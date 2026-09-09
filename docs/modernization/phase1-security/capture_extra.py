"""Phase 1 extra captures: reflected-XSS payloads and auth (401 vs bearer) transcripts.

Usage:
    python docs/modernization/phase1-security/capture_extra.py <prefix> [--bearer <token>]
                                                               [--base-url http://localhost:8000]

Writes into docs/modernization/phase1-security/:
    <prefix>-xss.html           raw HTML of /dashboard/billing?billing_ref=<script>alert(1)</script>
    <prefix>-xss.png            screenshot of that page (banner says whether the payload fired)
    <prefix>-xss-breakout.html  same with billing_ref="><script>alert(1)</script>, which closes
    <prefix>-xss-breakout.png   the reflected <input value="..."> attribute so the script runs
    <prefix>-auth.txt           curl-style transcript of unauthenticated requests and, when
                                --bearer is given, the same requests with an OAuth2 bearer token
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from urllib.error import HTTPError
from urllib.parse import quote
from urllib.request import Request, urlopen

from playwright.sync_api import Dialog, Page, sync_playwright

OUT = Path(__file__).parent
PAYLOADS = {
    "xss": "<script>alert(1)</script>",
    "xss-breakout": '"><script>alert(1)</script>',
}
AUTH_PATHS = [
    "/health",
    "/billing/invoices?period=2026-07",
    "/capacity/locations?requested_mbps=350",
]
SHOWN_HEADERS = {
    "www-authenticate",
    "content-type",
    "strict-transport-security",
    "content-security-policy",
    "x-content-type-options",
    "x-frame-options",
    "referrer-policy",
    "x-ratelimit-limit",
    "x-ratelimit-remaining",
}

BANNER_JS = """(t) => {
  const d = document.createElement('div');
  d.textContent = t;
  d.style.cssText = 'position:fixed;top:0;left:0;right:0;padding:10px 16px;'
    + 'font:600 15px monospace;color:#fff;z-index:9999;background:'
    + (t.includes('FIRED') ? '#be123c' : '#0f766e');
  document.body.appendChild(d);
}"""


def xss_path(payload: str) -> str:
    return "/dashboard/billing?billing_ref=" + quote(payload, safe="")


def fetch(url: str, bearer: str | None) -> tuple[int, dict[str, str], str]:
    req = Request(url)
    if bearer:
        req.add_header("Authorization", f"Bearer {bearer}")
    try:
        with urlopen(req) as resp:  # noqa: S310 - local dev server
            return resp.status, dict(resp.headers), resp.read().decode()
    except HTTPError as err:
        return err.code, dict(err.headers), err.read().decode()


def transcript(base: str, path: str, bearer: str | None) -> str:
    status, headers, body = fetch(base + path, bearer)
    try:
        body = json.dumps(json.loads(body), indent=2)
    except ValueError:
        pass
    if len(body) > 1500:
        body = body[:1500] + "\n... (truncated)"
    auth = f' -H "Authorization: Bearer {bearer[:12]}..."' if bearer else ""
    shown = {k: v for k, v in headers.items() if k.lower() in SHOWN_HEADERS}
    hdrs = "".join(f"{k}: {v}\n" for k, v in sorted(shown.items()))
    return f"$ curl -si{auth} {base}{path}\nHTTP {status}\n{hdrs}\n{body}\n"


def capture_xss(page: Page, base: str, name: str, payload: str, prefix: str) -> str:
    fired: list[str] = []

    def on_dialog(dialog: Dialog) -> None:
        fired.append(dialog.message)
        page.wait_for_timeout(1200)
        dialog.dismiss()

    page.on("dialog", on_dialog)
    page.goto(base + xss_path(payload), wait_until="networkidle")
    page.wait_for_timeout(1500)
    banner = (
        f"XSS payload FIRED: alert({fired[0]!r})" if fired else "XSS payload did NOT fire"
    )
    page.evaluate(BANNER_JS, f"{payload}  ->  {banner}")
    page.wait_for_timeout(300)
    page.screenshot(path=str(OUT / f"{prefix}-{name}.png"), full_page=True)
    page.remove_listener("dialog", on_dialog)
    return banner


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("prefix")
    ap.add_argument("--bearer", default=None)
    ap.add_argument("--base-url", default="http://localhost:8000")
    args = ap.parse_args()
    base = args.base_url.rstrip("/")

    chunks = [f"# {p}\n" + transcript(base, p, None) for p in AUTH_PATHS]
    if args.bearer:
        chunks += [
            f"# {p} (with bearer token)\n" + transcript(base, p, args.bearer) for p in AUTH_PATHS
        ]
    (OUT / f"{args.prefix}-auth.txt").write_text("\n".join(chunks))

    for name, payload in PAYLOADS.items():
        _, _, html = fetch(base + xss_path(payload), args.bearer)
        (OUT / f"{args.prefix}-{name}.html").write_text(html)

    with sync_playwright() as pw:
        browser = pw.chromium.launch()
        headers = {"Authorization": f"Bearer {args.bearer}"} if args.bearer else {}
        ctx = browser.new_context(
            viewport={"width": 1400, "height": 900}, extra_http_headers=headers
        )
        page = ctx.new_page()
        for name, payload in PAYLOADS.items():
            print(f"{name}: {capture_xss(page, base, name, payload, args.prefix)}")
        browser.close()


if __name__ == "__main__":
    main()
