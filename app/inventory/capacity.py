"""Capacity math.

Vantage always holds back a maintenance buffer on top of what is allocated: a
link is not considered spare capacity if we need it during a maintenance
window. The rule itself lives in the shared capacity-lib (also used by
meridian-telco): the buffer is 10% of total and
``available = total - allocated - maintenance_buffer``.
"""

from __future__ import annotations

from typing import Any, Dict

from app.inventory import capacity_lib

maintenance_buffer_mbps = capacity_lib.maintenance_buffer_mbps
can_support = capacity_lib.can_support


def available_capacity(total_mbps: int, allocated_mbps: int, maintenance_buffer_mbps: int | None = None) -> int:
    if maintenance_buffer_mbps is None:
        maintenance_buffer_mbps = capacity_lib.maintenance_buffer_mbps(total_mbps)
    return capacity_lib.available_capacity(total_mbps, allocated_mbps, maintenance_buffer_mbps)


def utilization_pct(total_mbps: int, allocated_mbps: int, maintenance_buffer_mbps: int = 0) -> float:
    if total_mbps <= 0:
        return 0.0
    return round((allocated_mbps + maintenance_buffer_mbps) * 100 / total_mbps, 2)


def site_capacity(site: Dict[str, Any]) -> Dict[str, Any]:
    total = int(site.get("total_capacity_mbps", 0))
    allocated = int(site.get("allocated_mbps", 0))
    buffer_mbps = maintenance_buffer_mbps(total)
    return {
        "total_mbps": total,
        "allocated_mbps": allocated,
        "maintenance_buffer_mbps": buffer_mbps,
        "available_mbps": available_capacity(total, allocated, buffer_mbps),
        "utilization_pct": utilization_pct(total, allocated, buffer_mbps),
    }
