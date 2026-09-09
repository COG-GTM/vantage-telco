"""Record the modernization evidence set (recording + full-page screenshots) for one phase.

Usage:
    python3 tools/capture/capture.py --out docs/modernization/phase1-security --prefix pre
    python3 tools/capture/capture.py --out ... --prefix post --token "$TOKEN"

Requires the app on http://localhost:8000 and system python3 with playwright + chromium.
Produces <prefix>-recording.mp4, <prefix>-dashboard.png, <prefix>-dashboard-billing.png,
<prefix>-capacity.png, <prefix>-swagger.png, <prefix>-xss.png, <prefix>-billing-invoices.json,
<prefix>-health.txt (and <prefix>-curl-auth.txt when --token is given).
"""

from __future__ import annotations

import argparse
import json
import shutil
import subprocess
import urllib.error
import urllib.request
from pathlib import Path

from playwright.sync_api import Page, sync_playwright

BASE = "http://localhost:8000"
XSS_PATH = "/v1/dashboard/billing?billing_ref=%3Cscript%3Ealert(1)%3C/script%3E"


def _scroll(page: Page) -> None:
    height = page.evaluate("document.body.scrollHeight")
    y = 0
    while y < height:
        y += 700
        page.evaluate(f"window.scrollTo(0, {y})")
        page.wait_for_timeout(150)
    page.evaluate("window.scrollTo(0, 0)")
    page.wait_for_timeout(300)


def _visit(page: Page, path: str, shot: Path | None) -> None:
    page.goto(BASE + path, wait_until="networkidle")
    page.wait_for_timeout(800)
    if shot is not None:
        page.screenshot(path=str(shot), full_page=True)
    _scroll(page)


def _curl(url: str, token: str | None) -> tuple[int, str, dict[str, str]]:
    req = urllib.request.Request(url)
    if token:
        req.add_header("Authorization", f"Bearer {token}")
    try:
        with urllib.request.urlopen(req, timeout=30) as resp:
            return resp.status, resp.read().decode(), dict(resp.headers)
    except urllib.error.HTTPError as exc:
        return exc.code, exc.read().decode(), dict(exc.headers)


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", required=True)
    ap.add_argument("--prefix", required=True, choices=["pre", "post"])
    ap.add_argument("--token", default=None, help="bearer token (post-Phase-1 runs)")
    args = ap.parse_args()
    out = Path(args.out)
    out.mkdir(parents=True, exist_ok=True)
    p = args.prefix

    # --- shell evidence -------------------------------------------------------
    status, body, _ = _curl(f"{BASE}/v1/billing/invoices?period=2026-07", args.token)
    if status == 200:
        (out / f"{p}-billing-invoices.json").write_text(
            json.dumps(json.loads(body), indent=4) + "\n"
        )
    status_h, body_h, _ = _curl(f"{BASE}/health", None)
    (out / f"{p}-health.txt").write_text(f"{body_h}\nHTTP {status_h}\n")

    lines = []
    invoices_url = f"{BASE}/v1/billing/invoices?period=2026-07"
    s, b, h = _curl(invoices_url, None)
    lines.append(f"$ curl -i '{invoices_url}'   # no Authorization header\nHTTP {s}")
    for k in (
        "www-authenticate",
        "strict-transport-security",
        "content-security-policy",
        "x-content-type-options",
        "x-frame-options",
    ):
        for hk, hv in h.items():
            if hk.lower() == k:
                lines.append(f"{hk}: {hv}")
    lines.append(f"\n{b[:400]}{'...' if len(b) > 400 else ''}\n")
    if args.token:
        s, b, _ = _curl(invoices_url, args.token)
        lines.append(f"$ curl -H 'Authorization: Bearer $TOKEN' '{invoices_url}'\nHTTP {s}")
        lines.append(f"{b[:400]}...\n")
    s, b, _ = _curl(BASE + XSS_PATH, args.token)
    lines.append(f"$ curl '{BASE}{XSS_PATH}' | grep -n billing_ref\nHTTP {s}")
    lines.extend(
        f"{n}: {ln.strip()}" for n, ln in enumerate(b.splitlines(), 1) if "billing_ref" in ln
    )
    (out / f"{p}-curl-auth.txt").write_text("\n".join(lines) + "\n")

    if args.token:
        pagination_lines = []
        pagination_cases = (
            ("/v1/resources", "resources"),
            ("/v1/circuits", "circuits"),
            ("/v1/billing/invoices?period=2026-07", "invoices"),
            ("/v1/network/devices", "devices"),
            ("/v1/capacity/locations", "locations"),
        )
        pagination_params = (
            "limit=50&offset=0",
            "limit=50&offset=100",
            "limit=50&offset=150",
            "offset=100000",
        )
        for path, list_key in pagination_cases:
            for params in pagination_params:
                separator = "&" if "?" in path else "?"
                url = f"{BASE}{path}{separator}{params}"
                status_p, body_p, _ = _curl(url, args.token)
                pagination_lines.append(
                    f"$ curl -H 'Authorization: Bearer $TOKEN' '{url}'\nHTTP {status_p}"
                )
                try:
                    payload = json.loads(body_p)
                    if isinstance(payload, dict):
                        top_level_keys = list(payload)
                        count = payload.get("count", "<absent>")
                        summary = [
                            f"keys: {top_level_keys}",
                            f"count: {count}",
                        ]
                        if "revenue_total" in payload:
                            summary.append(f"revenue_total: {payload['revenue_total']}")
                        values = payload.get(list_key)
                        summary.append(
                            f"{list_key}: {len(values) if isinstance(values, list) else '<absent>'}"
                        )
                        summary.append(
                            f"pagination: {payload['pagination']}"
                            if "pagination" in payload
                            else "pagination: <absent>"
                        )
                        pagination_lines.append("  " + "; ".join(summary))
                    else:
                        pagination_lines.append("  JSON top-level: <not an object>")
                except (TypeError, ValueError, json.JSONDecodeError):
                    pagination_lines.append("  JSON summary: <unavailable>")
                pagination_lines.append("")

        status_o, body_o, _ = _curl(f"{BASE}/openapi.json", args.token)
        try:
            openapi = json.loads(body_o)
            invoice_get = openapi["paths"]["/v1/billing/invoices"]["get"]
            parameter_names = [parameter["name"] for parameter in invoice_get.get("parameters", [])]
            version = openapi["info"]["version"]
            pagination_lines.extend(
                [
                    f"OpenAPI /billing/invoices GET parameter names: {parameter_names}",
                    f"OpenAPI info.version: {version}",
                ]
            )
        except (KeyError, TypeError, ValueError, json.JSONDecodeError) as exc:
            pagination_lines.append(f"OpenAPI summary: <unavailable: {exc}>")
        if status_o != 200:
            pagination_lines.append(f"OpenAPI HTTP {status_o}")
        (out / f"{p}-curl-pagination.txt").write_text("\n".join(pagination_lines) + "\n")

    # --- browser evidence -----------------------------------------------------
    video_dir = out / "_video"
    with sync_playwright() as pw:
        browser = pw.chromium.launch()
        headers = {"Authorization": f"Bearer {args.token}"} if args.token else {}
        ctx = browser.new_context(
            viewport={"width": 1400, "height": 900},
            record_video_dir=str(video_dir),
            record_video_size={"width": 1400, "height": 900},
            extra_http_headers=headers,
        )
        page = ctx.new_page()
        _visit(page, "/v1/dashboard", out / f"{p}-dashboard.png")
        _visit(page, "/v1/dashboard/billing", out / f"{p}-dashboard-billing.png")
        _visit(page, "/v1/dashboard/billing?period=2026-07", None)
        dialogs: list[str] = []

        def handle_dialog(dialog) -> None:
            dialogs.append(dialog.message)
            dialog.dismiss()

        page.on("dialog", handle_dialog)
        _visit(page, XSS_PATH, None)
        page.wait_for_timeout(1500)
        page.screenshot(path=str(out / f"{p}-xss.png"), full_page=True)
        # attribute-breakout variant of the same payload, to show markup injection visually
        _visit(page, XSS_PATH.replace("%3Cscript", "%22%3E%3Cscript", 1), None)
        page.wait_for_timeout(1500)
        page.screenshot(path=str(out / f"{p}-xss-breakout.png"), full_page=True)
        (out / f"{p}-xss-dialogs.txt").write_text(
            f"alert() dialogs fired while loading XSS payload pages: {dialogs!r}\n"
        )
        _visit(page, "/capacity", out / f"{p}-capacity.png")
        page.fill("#search", "RIV-01")
        page.wait_for_timeout(600)
        page.fill("#requested", "50")
        page.wait_for_timeout(800)
        page.fill("#requested", "5000")
        page.wait_for_timeout(800)
        try:
            _visit(page, "/docs", None)
            if args.token:
                page.click("button.authorize")
                page.wait_for_timeout(400)
                page.fill("input[type=text], input[type=password]", args.token)
                page.click("div.auth-btn-wrapper button.authorize")
                page.wait_for_timeout(400)
                page.click("button.btn-done")
                page.wait_for_timeout(400)
            operation = page.locator("#operations-billing-get_invoices_v1_billing_invoices_get")
            if not operation.count():
                operation = page.locator("#operations-billing-get_invoices_billing_invoices_get")
            if not operation.count():
                operation = page.locator("[id^='operations-billing-get_invoices']").first
            operation.click()
            page.wait_for_timeout(500)
            page.click("button.try-out__btn")
            page.wait_for_timeout(300)
            page.fill("input[placeholder='period']", "2026-07")
            page.click("button.execute")
            page.wait_for_timeout(2500)
            page.screenshot(path=str(out / f"{p}-swagger.png"), full_page=True)
            _scroll(page)
            page.wait_for_timeout(500)
        except Exception as exc:
            print(f"Warning: Swagger screenshot failed: {exc}")
        ctx.close()
        browser.close()

    webm = next(video_dir.glob("*.webm"))
    subprocess.run(
        [
            "ffmpeg",
            "-y",
            "-loglevel",
            "error",
            "-i",
            str(webm),
            "-c:v",
            "libx264",
            "-pix_fmt",
            "yuv420p",
            str(out / f"{p}-recording.mp4"),
        ],
        check=True,
    )
    shutil.rmtree(video_dir)
    print("\n".join(str(f) for f in sorted(out.glob(f"{p}-*"))))


if __name__ == "__main__":
    main()
