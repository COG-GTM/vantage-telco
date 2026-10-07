"""Capacity math, from the shared telco-rules library (DECISIONS.md D-07).

``available = total - allocated``, clamped at zero. No maintenance reserve is
withheld: ``maintenance_buffer_mbps`` is still carried on the record and in the
API so planning can see it, but it does not reduce sellable capacity.
"""

from __future__ import annotations

from typing import Any, Dict

import telco_rules


def available_capacity(total_mbps: int, allocated_mbps: int) -> int:
    return telco_rules.available_capacity(int(total_mbps), int(allocated_mbps))


def utilization_pct(total_mbps: int, allocated_mbps: int) -> float:
    return round(telco_rules.utilization_ratio_pct(int(total_mbps), int(allocated_mbps)), 2)


def can_support(total_mbps: int, allocated_mbps: int, requested_mbps: int) -> bool:
    return telco_rules.can_support(int(total_mbps), int(allocated_mbps), int(requested_mbps))


def site_capacity(site: Dict[str, Any]) -> Dict[str, Any]:
    total = int(site.get("total_capacity_mbps", 0))
    allocated = int(site.get("allocated_mbps", 0))
    return {
        "total_mbps": total,
        "allocated_mbps": allocated,
        "maintenance_buffer_mbps": int(site.get("maintenance_buffer_mbps", 0)),
        "available_mbps": available_capacity(total, allocated),
        "utilization_pct": utilization_pct(total, allocated),
    }
