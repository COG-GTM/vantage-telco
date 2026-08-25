"""Capacity math.

Meridian answers "what is left" with total minus allocated. Vantage also holds
back a maintenance buffer, on the grounds that capacity needed during a
maintenance window is not sellable. The buffer is carried on every record
either way; the policy decides whether it is withheld.
"""

from __future__ import annotations

from typing import Any

from oss.model import Site
from oss.policy import InventoryPolicy


def available_capacity(
    total_mbps: int, allocated_mbps: int, maintenance_buffer_mbps: int, policy: InventoryPolicy
) -> int:
    withheld = int(maintenance_buffer_mbps) if policy.withhold_maintenance_buffer else 0
    return max(int(total_mbps) - int(allocated_mbps) - withheld, 0)


def utilization_pct(
    total_mbps: int, allocated_mbps: int, maintenance_buffer_mbps: int, policy: InventoryPolicy
) -> float:
    if int(total_mbps) <= 0:
        return 0.0
    withheld = int(maintenance_buffer_mbps) if policy.withhold_maintenance_buffer else 0
    return round((int(allocated_mbps) + withheld) * 100 / int(total_mbps), 2)


def site_capacity(site: Site, policy: InventoryPolicy) -> dict[str, Any]:
    withheld = site.maintenance_buffer_mbps if policy.withhold_maintenance_buffer else 0
    return {
        "total_mbps": site.total_capacity_mbps,
        "allocated_mbps": site.allocated_mbps,
        "maintenance_buffer_mbps": site.maintenance_buffer_mbps,
        "withheld_buffer_mbps": withheld,
        "available_mbps": available_capacity(
            site.total_capacity_mbps, site.allocated_mbps, site.maintenance_buffer_mbps, policy
        ),
        "utilization_pct": utilization_pct(
            site.total_capacity_mbps, site.allocated_mbps, site.maintenance_buffer_mbps, policy
        ),
    }
