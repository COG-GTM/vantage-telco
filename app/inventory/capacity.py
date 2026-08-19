"""Capacity math.

The available-capacity rule lives in the shared ``inventory_rules`` package
(unified-inventory-rules) so meridian-oss and vantage-net compute it
identically. Vantage always holds back a maintenance buffer on top of what is
allocated: a link is not considered spare capacity if we need it during a
maintenance window, so ``available`` is total - allocated - maintenance_buffer.
"""

from __future__ import annotations

from typing import Any, Dict

from inventory_rules import available_capacity, utilization_pct

__all__ = ["available_capacity", "utilization_pct", "site_capacity"]


def site_capacity(site: Dict[str, Any]) -> Dict[str, Any]:
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
