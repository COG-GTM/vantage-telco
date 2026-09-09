import json
from pathlib import Path


def test_health(client):
    assert client.get("/health").json() == {"status": "ok"}


def test_resources_returns_the_full_footprint(client):
    body = client.get("/v1/resources").json()
    assert body["count"] == 97
    assert len(body["resources"]) == 50
    assert body["pagination"] == {"limit": 50, "offset": 0, "total": 97, "has_more": True}


def test_resource_by_uuid(client):
    uuid = client.get("/resources").json()["resources"][0]["device_uuid"]
    assert client.get(f"/resources/{uuid}").json()["device_uuid"] == uuid


def test_unknown_resource_is_404(client):
    assert client.get("/resources/does-not-exist").status_code == 404


def test_addressing_summary(client):
    body = client.get("/network/addressing").json()
    assert body["management_supernet"] == "10.20.0.0/16"
    assert body["address_references"] > 0


def test_billing_usage_summary_shows_unbilled_usage(client):
    body = client.get("/billing/usage-summary").json()
    assert body["unbilled_usage_mb"] > 0


def test_dashboard_renders(client):
    response = client.get("/v1/dashboard")
    assert response.status_code == 200
    assert "Vantage Net" in response.text


def test_billing_pagination(client):
    first = client.get(
        "/v1/billing/invoices", params={"period": "2026-07", "limit": 50, "offset": 0}
    ).json()
    assert len(first["invoices"]) == 50
    assert first["pagination"] == {"limit": 50, "offset": 0, "total": 200, "has_more": True}
    assert first["count"] == 200
    assert first["revenue_total"] == 1816527.27

    last = client.get(
        "/v1/billing/invoices", params={"period": "2026-07", "limit": 60, "offset": 180}
    ).json()
    assert len(last["invoices"]) == 20
    assert last["pagination"]["has_more"] is False

    empty = client.get(
        "/v1/billing/invoices", params={"period": "2026-07", "limit": 50, "offset": 100000}
    ).json()
    assert empty["invoices"] == []
    assert empty["pagination"]["has_more"] is False
    assert empty["count"] == 200

    for params in ({"limit": 0}, {"limit": 501}, {"offset": -1}):
        response = client.get("/v1/billing/invoices", params={"period": "2026-07", **params})
        assert response.status_code == 422


def test_other_list_endpoints_paginate(client, sales_client):
    for path, key, total in (
        ("/v1/resources", "resources", 97),
        ("/v1/circuits", "circuits", 60),
        ("/v1/network/devices", "devices", 74),
    ):
        body = client.get(path).json()
        assert body["pagination"]["total"] == body["count"] == total
        assert len(body[key]) == min(50, total)

    body = sales_client.get("/v1/capacity/locations").json()
    assert body["pagination"]["total"] == body["count"] == 22
    assert len(body["locations"]) == 22


def test_dashboard_pages_render_all_rows(client):
    response = client.get("/v1/dashboard")
    assert response.status_code == 200
    assert response.text.count("VANTAGE-BILL-") == 200

    billing = client.get("/v1/dashboard/billing")
    assert billing.status_code == 200
    assert ">200<" in billing.text


def test_capacity_page_renders_all_locations(sales_client):
    response = sales_client.get("/v1/capacity")
    assert response.status_code == 200
    assert "RIV-01" in response.text
    assert response.text.count("data-market=") == 22


def test_legacy_redirects_and_version(client, app_client):
    response = client.get("/dashboard/billing?period=2026-07", follow_redirects=False)
    assert response.status_code == 308
    assert response.headers["location"] == "/v1/dashboard/billing?period=2026-07"

    response = client.get("/billing/invoices?period=2026-07&limit=5", follow_redirects=False)
    assert response.status_code == 308
    assert response.headers["location"] == "/v1/billing/invoices?period=2026-07&limit=5"
    assert app_client.get("/health", follow_redirects=False).status_code == 200

    assert app_client.get("/v1/version").status_code == 401
    assert client.get("/v1/version").json() == {"version": "3.0.0"}

    openapi = app_client.get("/openapi.json").json()
    assert openapi["info"]["version"] == "3.0.0"
    parameters = openapi["paths"]["/v1/billing/invoices"]["get"]["parameters"]
    assert {"limit", "offset"} <= {parameter["name"] for parameter in parameters}


def test_templates_autoescape():
    from app.templating import templates

    assert templates.env.autoescape
    assert templates.env.autoescape("x.html") is True


def test_invoice_pagination_matches_phase0_baseline(billing_ops_client):
    baseline = json.loads(
        Path("docs/modernization/phase0-baseline/pre-billing-invoices.json").read_text()
    )
    invoices = []
    offset = 0
    while True:
        body = billing_ops_client.get(
            "/v1/billing/invoices",
            params={"period": "2026-07", "limit": 50, "offset": offset},
        ).json()
        assert body["count"] == baseline["count"]
        assert body["revenue_total"] == baseline["revenue_total"]
        invoices.extend(body["invoices"])
        if not body["pagination"]["has_more"]:
            break
        offset += 50
    assert json.dumps(invoices) == json.dumps(baseline["invoices"])
