from app.network import addressing


def test_all_devices_sit_in_the_management_supernet():
    assert all(addressing.in_supernet(ip) for ip in addressing.assigned_addresses())


def test_core_router_address_is_assigned():
    assert "10.20.4.17" in addressing.assigned_addresses()


def test_every_assigned_address_is_referenced_by_a_config():
    counts = addressing.referenced_addresses()
    missing = [ip for ip in addressing.assigned_addresses() if ip not in counts]
    assert missing == []


def test_no_orphaned_references():
    assert addressing.orphaned_references() == {}


def test_external_bgp_devices_are_flagged_in_the_address_plan():
    plan_names = set(addressing.address_plan()["external_bgp_devices"])
    assert plan_names == {d["device_name"] for d in addressing.external_bgp_devices()}


def test_reserved_ranges_come_from_telco_rules():
    assert str(addressing.MANAGEMENT_SUPERNET) == "10.20.0.0/16"
    assert {r["cidr"] for r in addressing.reserved_ranges()} == {"10.20.250.0/24", "10.20.251.0/24"}
    assert addressing.reserved_purpose("10.20.250.30") == "planned-agg-buildout"
    assert addressing.reserved_purpose("10.20.4.17") == ""
    summary = addressing.summary()
    assert summary["growth_pool_allocations"] == summary["reserved_range_allocations"]
