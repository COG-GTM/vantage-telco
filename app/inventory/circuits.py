"""Circuit roll-ups, from the shared telco-rules library (DECISIONS.md D-08).

A circuit counts when its lifecycle state is countable-active; its role does
not matter, so standby and failover circuits count towards the active count
and active capacity, the same as primaries.
"""

from __future__ import annotations

from typing import Any, Dict, Iterable, List

import telco_rules


def is_active(circuit: Dict[str, Any]) -> bool:
    return telco_rules.circuit_is_active_lifecycle(
        circuit.get("lifecycle_state", "") or "", (circuit.get("role", "PRIMARY") or "PRIMARY").upper()
    )


def active_circuits(circuits: Iterable[Dict[str, Any]]) -> List[Dict[str, Any]]:
    return [c for c in circuits if is_active(c)]


def active_count(circuits: Iterable[Dict[str, Any]]) -> int:
    return len(active_circuits(circuits))


def active_capacity_mbps(circuits: Iterable[Dict[str, Any]]) -> int:
    return sum(int(c.get("capacity_mbps", 0)) for c in active_circuits(circuits))
