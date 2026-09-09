import base64
import hashlib
import hmac
import json
import os
import subprocess
import sys
from pathlib import Path

import pytest

from app.security import (
    SCOPE_NOC,
    mint_token,
    rate_limiter,
    verify_token,
)

OPS_ROUTES = [
    "/resources",
    "/circuits",
    "/network/addressing",
    "/billing/invoices?period=2026-07",
    "/billing/usage-summary",
    "/dashboard",
    "/dashboard/billing",
]
CAPACITY_ROUTES = ["/capacity", "/capacity/locations"]


@pytest.mark.parametrize("path", OPS_ROUTES + CAPACITY_ROUTES)
def test_protected_routes_require_authentication(app_client, path):
    response = app_client.get(path)
    assert response.status_code == 401
    assert response.headers["WWW-Authenticate"] == "Bearer"


@pytest.mark.parametrize("path", ["/health", "/docs", "/openapi.json", "/docs/oauth2-redirect"])
def test_public_routes_do_not_require_authentication(app_client, path):
    assert app_client.get(path).status_code == 200


def test_redoc_is_disabled(app_client):
    assert app_client.get("/redoc").status_code == 404


@pytest.mark.parametrize("path", OPS_ROUTES)
def test_sales_scope_cannot_access_ops_routes(sales_client, path):
    assert sales_client.get(path).status_code == 403


@pytest.mark.parametrize("path", CAPACITY_ROUTES)
def test_ops_scope_cannot_access_capacity_routes(ops_client, path):
    assert ops_client.get(path).status_code == 403


def test_noc_invoice_response_redacts_pii(ops_client):
    response = ops_client.get("/billing/invoices?period=2026-07")
    body = response.json()
    assert response.status_code == 200
    assert body["count"] == 200
    assert body["revenue_total"] == 1816527.27
    assert all(
        invoice[field] == "[redacted]"
        for invoice in body["invoices"]
        for field in ("tax_id", "legal_name", "service_address")
    )


def test_billing_ops_invoice_response_matches_baseline(billing_ops_client):
    response = billing_ops_client.get("/billing/invoices?period=2026-07")
    baseline_path = Path("docs/modernization/phase0-baseline/pre-billing-invoices.json")
    baseline = json.loads(baseline_path.read_text())
    body = json.loads(response.text)
    assert body == baseline
    assert body["invoices"] == baseline["invoices"]


def test_tampered_token_is_rejected(app_client, token_for):
    token = token_for([SCOPE_NOC])
    payload, signature = token.split(".")
    replacement = "A" if signature[-1] != "A" else "B"
    response = app_client.get(
        "/resources",
        headers={"Authorization": f"Bearer {payload}.{signature[:-1]}{replacement}"},
    )
    assert response.status_code == 401


def test_expired_token_is_rejected(app_client):
    token = mint_token("expired-user", [SCOPE_NOC], ttl_seconds=-1)
    response = app_client.get("/resources", headers={"Authorization": f"Bearer {token}"})
    assert response.status_code == 401


def test_unknown_scope_payload_is_rejected(app_client):
    payload = {
        "sub": "test-user",
        "scopes": ["unknown"],
        "exp": 4_000_000_000,
    }
    payload_b64 = (
        base64.urlsafe_b64encode(
            json.dumps(payload, separators=(",", ":"), sort_keys=True).encode()
        )
        .rstrip(b"=")
        .decode()
    )
    signature = hmac.new(b"test-secret", payload_b64.encode(), hashlib.sha256).digest()
    token = f"{payload_b64}.{base64.urlsafe_b64encode(signature).rstrip(b'=').decode()}"
    response = app_client.get("/resources", headers={"Authorization": f"Bearer {token}"})
    assert response.status_code == 401


@pytest.mark.parametrize("parameter", ["period", "account_id", "billing_ref"])
def test_billing_dashboard_escapes_xss_parameters(client, parameter):
    response = client.get("/dashboard/billing", params={parameter: "<script>alert(1)</script>"})
    assert "<script>" not in response.text
    assert "&lt;script&gt;" in response.text


@pytest.mark.parametrize("parameter", ["period", "account_id", "billing_ref"])
def test_billing_dashboard_escapes_breakout_parameters(client, parameter):
    response = client.get("/dashboard/billing", params={parameter: '"><script>alert(1)</script>'})
    assert "<script>" not in response.text


def test_dashboard_escapes_period(client):
    response = client.get("/dashboard", params={"period": "<script>alert(1)</script>"})
    assert "<script>" not in response.text
    assert "&lt;script&gt;" in response.text


def test_security_headers_are_present(client, app_client):
    expected = {
        "Strict-Transport-Security": "max-age=31536000; includeSubDomains",
        "Content-Security-Policy": (
            "default-src 'self'; script-src 'self' 'unsafe-inline' "
            "https://cdn.jsdelivr.net; style-src 'self' 'unsafe-inline' "
            "https://cdn.jsdelivr.net; img-src 'self' data: "
            "https://fastapi.tiangolo.com; frame-ancestors 'none'"
        ),
        "X-Content-Type-Options": "nosniff",
        "X-Frame-Options": "DENY",
        "Referrer-Policy": "no-referrer",
    }
    for response in (
        client.get("/health"),
        app_client.get("/resources"),
        client.get("/dashboard"),
    ):
        for header, value in expected.items():
            assert response.headers[header] == value


def test_rate_limit_exempts_health(ops_client):
    rate_limiter.limit_per_minute = 3
    rate_limiter.reset()
    for _ in range(3):
        assert ops_client.get("/resources").status_code == 200
    response = ops_client.get("/resources")
    assert response.status_code == 429
    assert response.json() == {"detail": "rate limit exceeded"}
    assert response.headers["Retry-After"] == "60"
    assert ops_client.get("/health").status_code == 200


def test_cli_mints_token():
    result = subprocess.run(
        [sys.executable, "-m", "app.security", "--scopes", "noc", "billing-ops"],
        check=True,
        capture_output=True,
        text=True,
        env={**os.environ, "VANTAGE_AUTH_DEV_SECRET": "test-secret"},
    )
    principal = verify_token(result.stdout.strip(), secret="test-secret")
    assert principal.scopes == {"noc", "billing-ops"}


def test_mint_token_rejects_unknown_scope():
    with pytest.raises(ValueError):
        mint_token("test-user", ["unknown"])


def test_protected_route_returns_503_without_secret(app_client, token_for, monkeypatch):
    token = token_for([SCOPE_NOC])
    monkeypatch.delenv("VANTAGE_AUTH_DEV_SECRET")
    response = app_client.get("/resources", headers={"Authorization": f"Bearer {token}"})
    assert response.status_code == 503
