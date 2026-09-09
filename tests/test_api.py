def test_health(client):
    assert client.get("/health").json() == {"status": "ok"}


def test_resources_returns_the_full_footprint(client):
    body = client.get("/resources").json()
    assert body["count"] == 97
    assert len(body["resources"]) == 97


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
    response = client.get("/dashboard")
    assert response.status_code == 200
    assert "Vantage Net" in response.text
