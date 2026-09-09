import pytest
from fastapi.testclient import TestClient

from app import security
from app.main import app
from app.network import addressing
from app.templating import templates

client = TestClient(app)


def test_health():
    assert client.get("/health").json() == {"status": "ok"}


def test_resources_returns_the_full_footprint():
    body = client.get("/resources").json()
    assert body["total"] == 97
    assert len(body["items"]) == 50


def test_resource_by_uuid():
    uuid = client.get("/resources?limit=500").json()["items"][0]["device_uuid"]
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


def test_pagination_defaults_and_bounds():
    body = client.get("/resources").json()
    assert body["limit"] == 50
    assert body["offset"] == 0
    assert body["total"] == 97
    assert len(body["items"]) == 50
    assert client.get("/resources?limit=500").status_code == 200
    for query in ("limit=501", "limit=0", "offset=-1", "limit=abc"):
        assert client.get(f"/resources?{query}").status_code == 422


def test_pagination_offset_beyond_total():
    body = client.get("/resources?offset=1000").json()
    assert body["items"] == []
    assert body["total"] == 97


@pytest.mark.parametrize("path", ["/resources", "/billing/invoices?period=2026-07"])
def test_pagination_pages_are_stable_and_concatenate(path):
    full = client.get(f"{path}&limit=500" if "?" in path else f"{path}?limit=500").json()
    pages = [
        client.get(
            f"{path}&limit=40&offset={offset}"
            if "?" in path
            else f"{path}?limit=40&offset={offset}"
        ).json()
        for offset in range(0, full["total"], 40)
    ]
    assert all(page["total"] == full["total"] for page in pages)
    assert [item for page in pages for item in page["items"]] == full["items"]


def test_circuit_rollups_cover_full_filtered_list():
    first = client.get("/circuits?limit=1").json()
    second = client.get("/circuits?limit=1&offset=1").json()
    assert first["active_count"] == second["active_count"]
    assert first["active_capacity_mbps"] == second["active_capacity_mbps"]


def test_network_list_endpoints_use_envelopes():
    devices = client.get("/network/devices").json()
    assert {"items", "total", "limit", "offset"} <= devices.keys()
    address = addressing.devices()[0]["mgmt_ip"]
    references = client.get("/network/references", params={"address": address}).json()
    assert {"items", "total", "limit", "offset", "address"} <= references.keys()


def test_noc_billing_invoices_are_redacted(token_for):
    response = TestClient(app).get(
        "/billing/invoices?period=2026-07&limit=1",
        headers=token_for([security.SCOPE_NOC]),
    )
    assert response.status_code == 200
    invoice = response.json()["items"][0]
    assert all(invoice[field] == security.REDACTED for field in security.PII_FIELDS)


@pytest.mark.parametrize(
    "path",
    [
        "/resources?limit=5",
        "/circuits",
        "/billing/invoices?period=2026-07&limit=3",
        "/network/addressing",
        "/capacity/locations?requested_mbps=350",
    ],
)
def test_legacy_and_v1_json_bodies_match(path):
    assert client.get(path).content == client.get(f"/v1{path}").content


@pytest.mark.parametrize("path", ["/dashboard", "/dashboard/billing?period=2026-07", "/capacity"])
def test_legacy_and_v1_html_bodies_match(path):
    legacy = client.get(path).text
    versioned = client.get(f"/v1{path}").text
    assert versioned.replace("/v1/dashboard/billing", "/dashboard/billing") == legacy


def test_openapi_versions_routes_and_health():
    schema = app.openapi()
    assert "/v1/resources" in schema["paths"]
    assert schema["paths"]["/v1/resources"]["get"].get("deprecated") is not True
    assert schema["paths"]["/resources"]["get"]["deprecated"] is True
    assert "/health" in schema["paths"]
    assert "/v1/health" not in schema["paths"]


def test_dashboards_render_template_content():
    dashboard = client.get("/dashboard").text
    billing = client.get("/dashboard/billing?period=2026-07").text
    capacity = client.get("/capacity").text
    assert "Vantage Net &middot; Inventory &amp; Billing" in dashboard
    assert "<h2>Invoices" in dashboard and "2026-07" in dashboard
    assert "Invoice Register" in billing and 'value="2026-07"' in billing
    assert "Capacity Check" in capacity and 'id="rows"' in capacity
    assert "data-search=" in capacity


def test_templates_autoescape():
    assert templates.env.autoescape is True
    assert templates.env.from_string("{{ x }}").render(x="<b>") == "&lt;b&gt;"
