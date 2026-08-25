"""Circuit roll-ups.

Meridian counts every circuit it owns, standby included: the fibre is lit and
it is on the books. Vantage counts only the roles carrying customer traffic,
because standby and failover capacity is not spare capacity.
"""

from __future__ import annotations

from collections.abc import Iterable

from oss.model import Circuit
from oss.policy import InventoryPolicy

REDUNDANT_ROLES = frozenset({"STANDBY", "FAILOVER"})


def is_active(circuit: Circuit, policy: InventoryPolicy) -> bool:
    if circuit.lifecycle_state != "ACTIVE":
        return False
    if policy.active_circuit_roles is None:
        return True
    return (circuit.role or "PRIMARY").upper() in policy.active_circuit_roles


def active_circuits(circuits: Iterable[Circuit], policy: InventoryPolicy) -> list[Circuit]:
    return [c for c in circuits if is_active(c, policy)]


def active_count(circuits: Iterable[Circuit], policy: InventoryPolicy) -> int:
    return len(active_circuits(circuits, policy))


def active_capacity_mbps(circuits: Iterable[Circuit], policy: InventoryPolicy) -> int:
    return sum(c.capacity_mbps for c in active_circuits(circuits, policy))
