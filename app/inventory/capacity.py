"""Capacity math.

Vantage always holds back a maintenance buffer on top of what is allocated: a
link is not considered spare capacity if we need it during a maintenance
window. ``available`` is therefore total - allocated - maintenance_buffer.
"""

from __future__ import annotations

from typing import Any


def available_capacity(
    total_mbps: int, allocated_mbps: int, maintenance_buffer_mbps: int = 0
) -> int:
    return max(total_mbps - allocated_mbps - maintenance_buffer_mbps, 0)


def utilization_pct(
    total_mbps: int, allocated_mbps: int, maintenance_buffer_mbps: int = 0
) -> float:
    if total_mbps <= 0:
        return 0.0
    return round((allocated_mbps + maintenance_buffer_mbps) * 100 / total_mbps, 2)


def site_capacity(site: dict[str, Any]) -> dict[str, Any]:
    total = int(site.get("total_capacity_mbps", 0))
    allocated = int(site.get("allocated_mbps", 0))
    buffer_mbps = int(site.get("maintenance_buffer_mbps", 0))
    return {
        "total_mbps": total,
        "allocated_mbps": allocated,
        "maintenance_buffer_mbps": buffer_mbps,
        "available_mbps": available_capacity(total, allocated, buffer_mbps),
        "utilization_pct": utilization_pct(total, allocated, buffer_mbps),
    }
