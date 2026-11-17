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


def test_referenced_addresses_reparses_changed_file(tmp_path, monkeypatch):
    monkeypatch.setattr(addressing, "CONFIG_ROOT", tmp_path)
    config = tmp_path / "routing.yaml"
    config.write_text("peer: 10.20.9.9\n")
    assert addressing.referenced_addresses() == {"10.20.9.9": 1}

    config.write_text("peer: 10.20.9.9\nbackup: 10.20.9.10\n")
    assert addressing.referenced_addresses() == {"10.20.9.9": 1, "10.20.9.10": 1}
