"""Inventory differences: the maintenance buffer and the standby circuit."""

from __future__ import annotations

from oss.inventory.capacity import available_capacity, utilization_pct
from oss.inventory.circuits import active_capacity_mbps, active_count
from oss.inventory.locations import enrich_location
from oss.model import Circuit, Location
from oss.policy import MERIDIAN, VANTAGE
from oss.service import get_estate

MER = MERIDIAN.inventory
VAN = VANTAGE.inventory


def circuit(circuit_id: str, role: str, capacity_mbps: int, state: str) -> Circuit:
    return Circuit(
        circuit_id=circuit_id,
        name=f"circuit {circuit_id}",
        a_site_id="S1",
        z_site_id="S2",
        capacity_mbps=capacity_mbps,
        allocated_mbps=0,
        role=role,
        lifecycle_state=state,
    )


CIRCUITS = [
    circuit("C1", "PRIMARY", 1000, "ACTIVE"),
    circuit("C2", "STANDBY", 1000, "ACTIVE"),
    circuit("C3", "PRIMARY", 500, "DECOMMISSIONED"),
]

LOCATION = Location(
    location_code="L1",
    customer_name="Acme",
    location_name="Acme HQ",
    market_id="M1",
    total_capacity_mbps=1000,
    allocated_mbps=800,
    maintenance_buffer_mbps=150,
)


class TestMaintenanceBuffer:
    def test_meridian_sells_the_maintenance_buffer(self) -> None:
        assert available_capacity(1000, 800, 150, MER) == 200
        assert utilization_pct(1000, 800, 150, MER) == 80.0

    def test_vantage_holds_it_back(self) -> None:
        assert available_capacity(1000, 800, 150, VAN) == 50
        assert utilization_pct(1000, 800, 150, VAN) == 95.0

    def test_capacity_never_goes_negative(self) -> None:
        assert available_capacity(1000, 950, 150, VAN) == 0

    def test_the_same_order_is_serviceable_on_one_estate_and_not_the_other(self) -> None:
        assert enrich_location(LOCATION, MER, requested_mbps=100)["can_support"] is True
        assert enrich_location(LOCATION, VAN, requested_mbps=100)["can_support"] is False


class TestCircuitRoles:
    def test_meridian_counts_standby_fibre_as_active(self) -> None:
        assert active_count(CIRCUITS, MER) == 2
        assert active_capacity_mbps(CIRCUITS, MER) == 2000

    def test_vantage_counts_only_circuits_carrying_traffic(self) -> None:
        assert active_count(CIRCUITS, VAN) == 1
        assert active_capacity_mbps(CIRCUITS, VAN) == 1000

    def test_neither_estate_counts_a_decommissioned_circuit(self) -> None:
        assert all(c.circuit_id != "C3" for c in CIRCUITS if active_count([c], MER))


class TestEstateRollups:
    def test_the_roll_up_reports_which_rule_produced_it(self) -> None:
        assert get_estate("meridian").circuit_summary()["counts_redundant_roles"] is True
        assert get_estate("vantage").circuit_summary()["counts_redundant_roles"] is False

    def test_the_seeded_books_load_and_are_not_empty(self) -> None:
        for name in ("meridian", "vantage"):
            estate = get_estate(name)
            assert estate.sites() and estate.circuits() and estate.locations()
