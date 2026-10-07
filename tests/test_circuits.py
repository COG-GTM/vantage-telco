from app.inventory.circuits import active_capacity_mbps, active_count, is_active
from app.inventory.repository import list_circuits


def test_standby_and_failover_circuits_count():
    assert is_active({"lifecycle_state": "ACTIVE", "role": "STANDBY"})
    assert is_active({"lifecycle_state": "ACTIVE", "role": "FAILOVER"})
    assert is_active({"lifecycle_state": "ACTIVE", "role": "PRIMARY"})


def test_only_active_lifecycle_circuits_count():
    assert not is_active({"lifecycle_state": "RETIRED", "role": "PRIMARY"})
    assert not is_active({"lifecycle_state": "MAINTENANCE", "role": "PRIMARY"})
    assert not is_active({"lifecycle_state": "PLANNED", "role": "PRIMARY"})


def test_active_rollups_include_redundant_circuits():
    circuits = list_circuits()
    assert active_count(circuits) == sum(1 for c in circuits if c["lifecycle_state"] == "ACTIVE")
    assert active_count(circuits) < len(circuits)
    assert active_capacity_mbps(circuits) == sum(
        c["capacity_mbps"] for c in circuits if is_active(c)
    )
