from app.inventory.capacity import available_capacity, site_capacity, utilization_pct
from app.inventory.repository import get_site, list_circuits


def test_available_capacity_holds_no_maintenance_reserve():
    assert available_capacity(1000, 600) == 400


def test_available_capacity_never_negative():
    assert available_capacity(100, 150) == 0


def test_utilization_is_allocated_over_total():
    assert utilization_pct(1000, 600) == 60.0
    assert utilization_pct(3000, 1001) == 33.37


def test_downtown_fiber_ring_reports_400_mbps():
    circuit = list_circuits(circuit_id="VC-BOS-0118")[0]
    assert circuit["maintenance_buffer_mbps"] == 150
    assert circuit["available_mbps"] == 400


def test_site_capacity_shape():
    site = get_site(list_sites_uuid())
    capacity = site_capacity(site)
    assert set(capacity) == {
        "total_mbps",
        "allocated_mbps",
        "maintenance_buffer_mbps",
        "available_mbps",
        "utilization_pct",
    }


def list_sites_uuid():
    from app.inventory.repository import list_sites

    return list_sites()[0]["device_uuid"]
