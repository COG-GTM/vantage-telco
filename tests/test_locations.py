from fastapi.testclient import TestClient

from app.inventory.locations import get_location, list_locations
from app.main import app

client = TestClient(app)


def test_availability_withholds_the_maintenance_buffer():
    location = get_location("RIV-01")
    assert (location["total_capacity_mbps"], location["allocated_mbps"]) == (1000, 600)
    assert location["maintenance_buffer_mbps"] == 150
    assert location["available_mbps"] == 250


def test_first_location_is_riv_01():
    assert list_locations()[0]["location_code"] == "RIV-01"


def test_requested_bandwidth_drives_the_verdict():
    assert get_location("RIV-01", requested_mbps=250)["can_support"] is True
    assert get_location("RIV-01", requested_mbps=400)["can_support"] is False


def test_search_and_market_filters():
    assert [location["location_code"] for location in list_locations(search="riverside")] == [
        "RIV-01"
    ]
    assert all(
        location["market_id"] == "BOS-12"
        for location in list_locations(market_id="BOS-12")
    )


def test_capacity_locations_endpoint():
    body = client.get("/capacity/locations", params={"requested_mbps": 400}).json()
    assert body["rule"] == "available = total_capacity - allocated - maintenance_buffer"
    assert body["locations"][0]["location_code"] == "RIV-01"
    assert body["locations"][0]["can_support"] is False


def test_unknown_location_is_404():
    assert client.get("/capacity/locations/NOPE-99").status_code == 404


def test_capacity_page_renders_the_buffer_column():
    response = client.get("/capacity")
    assert response.status_code == 200
    assert "Maint. buffer" in response.text
    assert "RIV-01" in response.text
