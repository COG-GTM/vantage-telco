from __future__ import annotations

import time

import jwt
import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from app import security
from app.billing import invoices as invoice_service
from app.main import app, cors_origins
from app.middleware import RateLimitMiddleware


@pytest.fixture
def anon() -> TestClient:
    return TestClient(app)


def _claims(**overrides):
    now = int(time.time())
    claims = {
        "iss": security.settings().issuer,
        "aud": security.settings().audience,
        "sub": "security-test",
        "iat": now,
        "exp": now + 3600,
        "scope": security.SCOPE_NOC,
    }
    claims.update(overrides)
    return claims


@pytest.mark.parametrize(
    "path",
    [
        "/resources",
        "/circuits",
        "/network/addressing",
        "/billing/invoices",
        "/capacity/locations",
        "/capacity",
        "/dashboard",
        "/dashboard/billing",
    ],
)
def test_protected_routes_require_bearer(anon, path):
    response = anon.get(path)
    assert response.status_code == 401
    assert response.headers["WWW-Authenticate"].startswith("Bearer")


def test_health_is_open(anon):
    assert anon.get("/health").json() == {"status": "ok"}


@pytest.mark.parametrize(
    "token",
    [
        "not-a-jwt",
        security.mint_dev_token([security.SCOPE_NOC], ttl_seconds=-3600),
        jwt.encode(_claims(aud="wrong-audience"), "test-secret-not-for-prod", algorithm="HS256"),
        jwt.encode(
            _claims(iss="https://wrong.example/"),
            "test-secret-not-for-prod",
            algorithm="HS256",
        ),
        jwt.encode(_claims(), "different-secret", algorithm="HS256"),
        jwt.encode(_claims(), key=None, algorithm="none"),
    ],
)
def test_invalid_tokens_are_unauthorized(anon, token):
    response = anon.get("/resources", headers={"Authorization": f"Bearer {token}"})
    assert response.status_code == 401


@pytest.mark.parametrize(
    ("scope", "path"),
    [
        (security.SCOPE_INVENTORY_READ, "/resources"),
        (security.SCOPE_NETWORK_READ, "/network/addressing"),
        (security.SCOPE_SALES_ENGINEERING, "/capacity/locations"),
        (security.SCOPE_BILLING_OPS, "/billing/invoices"),
        (security.SCOPE_NOC, "/dashboard"),
        (security.SCOPE_NOC, "/dashboard/billing"),
    ],
)
def test_correct_scope_allows_router(token_for, scope, path):
    assert TestClient(app).get(path, headers=token_for([scope])).status_code == 200


def test_roles_claim_allows_router():
    token = jwt.encode(
        _claims(scope=None, roles=[security.SCOPE_NETWORK_READ]),
        "test-secret-not-for-prod",
        algorithm="HS256",
    )
    assert TestClient(app).get(
        "/network/addressing", headers={"Authorization": f"Bearer {token}"}
    ).status_code == 200


@pytest.mark.parametrize(
    ("scope", "path"),
    [
        (security.SCOPE_SALES_ENGINEERING, "/billing/invoices"),
        (security.SCOPE_SALES_ENGINEERING, "/dashboard"),
        (security.SCOPE_NOC, "/capacity/locations"),
    ],
)
def test_wrong_scope_is_forbidden(token_for, scope, path):
    assert TestClient(app).get(path, headers=token_for([scope])).status_code == 403


def test_billing_pii_policy(token_for):
    expected = invoice_service.list_invoices(period="2026-07")
    billing = TestClient(app).get(
        "/billing/invoices?period=2026-07",
        headers=token_for([security.SCOPE_BILLING_OPS]),
    ).json()["invoices"]
    assert billing == expected

    noc = TestClient(app).get(
        "/billing/invoices?period=2026-07",
        headers=token_for([security.SCOPE_NOC]),
    ).json()["invoices"]
    redacted = [
        security.redact_pii(invoice, security.Principal("test", frozenset()))
        for invoice in expected
    ]
    assert noc == redacted
    assert all(
        invoice[field] == security.REDACTED
        for invoice in noc
        for field in security.PII_FIELDS
    )


def test_dashboard_pii_policy(token_for):
    expected_name = invoice_service.list_invoices(period="2026-07")[0]["legal_name"]
    noc = TestClient(app).get(
        "/dashboard?period=2026-07", headers=token_for([security.SCOPE_NOC])
    )
    billing = TestClient(app).get(
        "/dashboard?period=2026-07", headers=token_for([security.SCOPE_BILLING_OPS])
    )
    assert security.REDACTED in noc.text
    assert expected_name not in noc.text
    assert expected_name in billing.text


@pytest.mark.parametrize(
    "query",
    [
        {"billing_ref": "<script>alert(1)</script>"},
        {"period": '"><script>alert(1)</script>'},
        {"account_id": '"><script>alert(1)</script>'},
    ],
)
def test_dashboard_reflections_are_escaped(token_for, query):
    response = TestClient(app).get(
        "/dashboard/billing", params=query, headers=token_for([security.SCOPE_NOC])
    )
    assert response.status_code == 200
    assert "<script>alert(1)</script>" not in response.text
    assert "&lt;script&gt;" in response.text


def test_security_headers_on_success_and_unauthorized(anon):
    names = {
        "strict-transport-security",
        "content-security-policy",
        "x-content-type-options",
        "x-frame-options",
        "referrer-policy",
    }
    preflight = anon.options(
        "/resources",
        headers={
            "Origin": "https://evil.example",
            "Access-Control-Request-Method": "GET",
        },
    )
    assert preflight.status_code == 400
    for response in (anon.get("/health"), anon.get("/resources"), preflight):
        assert names <= set(response.headers)


def test_rate_limit_middleware():
    limited = FastAPI()
    limited.add_middleware(RateLimitMiddleware, limit_per_minute=3)

    @limited.get("/x")
    def x():
        return {"ok": True}

    @limited.get("/health")
    def health():
        return {"status": "ok"}

    client = TestClient(limited)
    assert client.get("/x").headers["X-RateLimit-Remaining"] == "2"
    assert client.get("/x").headers["X-RateLimit-Remaining"] == "1"
    assert client.get("/x").headers["X-RateLimit-Remaining"] == "0"
    limited_response = client.get("/x")
    assert limited_response.status_code == 429
    assert limited_response.json() == {"detail": "rate limit exceeded"}
    assert int(limited_response.headers["Retry-After"]) >= 1
    assert client.get("/health").status_code == 200


def test_cors_rejects_unconfigured_origin(client):
    response = client.get("/health", headers={"Origin": "https://evil.example"})
    assert "access-control-allow-origin" not in response.headers


def test_cors_origins_parser(monkeypatch):
    monkeypatch.setenv("VANTAGE_CORS_ORIGINS", " https://a.example,https://b.example ")
    assert cors_origins() == ["https://a.example", "https://b.example"]


def test_mint_dev_token_requires_secret(monkeypatch):
    monkeypatch.delenv("VANTAGE_AUTH_DEV_SECRET", raising=False)
    security.reset_settings_cache()
    with pytest.raises(RuntimeError, match="VANTAGE_AUTH_DEV_SECRET"):
        security.mint_dev_token([security.SCOPE_NOC])
    monkeypatch.setenv("VANTAGE_AUTH_DEV_SECRET", "test-secret-not-for-prod")
    security.reset_settings_cache()


@pytest.mark.parametrize(
    ("claims", "expected"),
    [
        ({"scope": "a b"}, {"a", "b"}),
        ({"scope": ["a", "b"]}, {"a", "b"}),
        ({"scp": ["a", "b"]}, {"a", "b"}),
        ({"roles": ["a", "b"]}, {"a", "b"}),
        ({"roles": "a b"}, {"a", "b"}),
        ({}, set()),
    ],
)
def test_extract_scopes(claims, expected):
    assert security.extract_scopes(claims) == frozenset(expected)
