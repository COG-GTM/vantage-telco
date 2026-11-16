from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


def test_health():
    assert client.get("/health").json() == {"status": "ok"}


def test_resources_returns_the_full_footprint():
    body = client.get("/resources").json()
    assert body["count"] == 97
    assert len(body["resources"]) == 97


def test_resource_by_uuid():
    uuid = client.get("/resources").json()["resources"][0]["device_uuid"]
    assert client.get(f"/resources/{uuid}").json()["device_uuid"] == uuid


def test_unknown_resource_is_404():
    assert client.get("/resources/does-not-exist").status_code == 404


def test_addressing_summary():
    body = client.get("/network/addressing").json()
    assert body["management_supernet"] == "10.20.0.0/16"
    assert body["address_references"] > 0


def test_billing_usage_summary_shows_unbilled_usage():
    body = client.get("/billing/usage-summary").json()
    assert body["unbilled_usage_mb"] > 0


def test_dashboard_renders():
    response = client.get("/dashboard")
    assert response.status_code == 200
    assert "Vantage Net" in response.text


XSS_PAYLOAD = '"><script>alert(1)</script>'
ESCAPED_PAYLOAD = "&quot;&gt;&lt;script&gt;alert(1)&lt;/script&gt;"


def test_billing_dashboard_escapes_query_params():
    for param in ("account_id", "billing_ref", "period"):
        response = client.get("/dashboard/billing", params={param: XSS_PAYLOAD})
        assert response.status_code == 200
        assert "<script>" not in response.text, param
        assert f'name="{param}" value="{ESCAPED_PAYLOAD}"' in response.text, param


def test_dashboard_escapes_period():
    response = client.get("/dashboard", params={"period": XSS_PAYLOAD})
    assert response.status_code == 200
    assert "<script>" not in response.text
    assert ESCAPED_PAYLOAD in response.text


def test_billing_dashboard_round_trips_filter_values():
    response = client.get(
        "/dashboard/billing",
        params={"period": "2026-07", "account_id": "VANTAGE-BILL-0001", "billing_ref": "TN-0001"},
    )
    assert 'name="period" value="2026-07"' in response.text
    assert 'name="account_id" value="VANTAGE-BILL-0001"' in response.text
    assert 'name="billing_ref" value="TN-0001"' in response.text


def test_dashboards_escape_seed_data(monkeypatch):
    from app.billing import invoices as invoice_service

    original = invoice_service.list_invoices

    def tainted(*args, **kwargs):
        rows = original(*args, **kwargs)
        return [{**row, "legal_name": "<script>alert('seed')</script>"} for row in rows]

    monkeypatch.setattr(invoice_service, "list_invoices", tainted)
    for path in ("/dashboard", "/dashboard/billing"):
        body = client.get(path).text
        assert "<script>" not in body, path
        assert "&lt;script&gt;alert(&#x27;seed&#x27;)&lt;/script&gt;" in body, path
