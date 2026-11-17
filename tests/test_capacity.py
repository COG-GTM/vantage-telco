import capacity_core

from app.inventory.capacity import available_capacity, can_support, site_capacity, utilization_pct
from app.inventory.repository import get_site, list_circuits


def test_available_capacity_subtracts_maintenance_buffer():
    assert available_capacity(1000, 600, 150) == 250


def test_available_capacity_never_negative():
    assert available_capacity(100, 90, 50) == 0


def test_utilization_includes_buffer():
    assert utilization_pct(1000, 600, 150) == 75.0


def test_downtown_fiber_ring_reports_250_mbps():
    circuit = list_circuits(circuit_id="VC-BOS-0118")[0]
    assert circuit["available_mbps"] == 250


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


def test_buffer_defaults_to_zero():
    assert available_capacity(1000, 600) == 400
    assert utilization_pct(1000, 600) == 60.0


def test_utilization_rounds_to_two_decimals():
    assert utilization_pct(3, 1) == 33.33
    assert utilization_pct(0, 50, 10) == 0.0
    # exact decimal ties round half-to-even: 0.025 -> 0.02, 0.035 -> 0.04
    assert utilization_pct(4000, 1) == 0.02
    assert utilization_pct(4000, 1, 0) == utilization_pct(4000, 0, 1)
    assert utilization_pct(20000, 7) == 0.04


def test_can_support_is_requested_within_available():
    assert can_support(1000, 600, 250, 150) is True
    assert can_support(1000, 600, 251, 150) is False


def test_delegates_to_shared_capacity_core():
    for args in [(1000, 600, 150), (1234, 567, 89), (100, 90, 50), (0, 0, 0)]:
        assert available_capacity(*args) == capacity_core.available_capacity(*args)
        assert utilization_pct(*args) == capacity_core.utilization_pct(*args)
