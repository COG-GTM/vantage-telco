"""Capacity math.

Vantage always holds back a maintenance buffer on top of what is allocated: a
link is not considered spare capacity if we need it during a maintenance
window. ``available`` is therefore total - allocated - maintenance_buffer.

The rule itself lives in the shared ``capacity_core`` package
(COG-GTM/telco-capacity-core), which meridian-telco also uses, so both
services compute identical figures. This module keeps Vantage's signatures and
the ``site_capacity()`` shape.
"""

from __future__ import annotations

from typing import Any, Dict

import capacity_core


def available_capacity(total_mbps: int, allocated_mbps: int, maintenance_buffer_mbps: int = 0) -> int:
    return capacity_core.available_capacity(total_mbps, allocated_mbps, maintenance_buffer_mbps)


def utilization_pct(total_mbps: int, allocated_mbps: int, maintenance_buffer_mbps: int = 0) -> float:
    return capacity_core.utilization_pct(total_mbps, allocated_mbps, maintenance_buffer_mbps)


def can_support(
    total_mbps: int, allocated_mbps: int, requested_mbps: int, maintenance_buffer_mbps: int = 0
) -> bool:
    return capacity_core.can_support(total_mbps, allocated_mbps, requested_mbps, maintenance_buffer_mbps)


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
