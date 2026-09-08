"""Capacity calculations shared across telco estates."""

from __future__ import annotations

from typing import Any, Dict

from telco_capacity import available_capacity, utilization_pct


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
