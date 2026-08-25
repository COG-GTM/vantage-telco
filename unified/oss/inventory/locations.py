"""Serviceable customer locations.

The sales desk asks one question: can we sell this bandwidth at this location
today. The answer uses the estate's capacity rule, so the same location is
sellable on Meridian terms and may not be on Vantage terms.
"""

from __future__ import annotations

from collections.abc import Iterable
from typing import Any

from oss.inventory.capacity import available_capacity, utilization_pct
from oss.model import Location
from oss.policy import InventoryPolicy


def enrich_location(
    location: Location, policy: InventoryPolicy, requested_mbps: int = 0
) -> dict[str, Any]:
    available = available_capacity(
        location.total_capacity_mbps,
        location.allocated_mbps,
        location.maintenance_buffer_mbps,
        policy,
    )
    return {
        "location_code": location.location_code,
        "customer_name": location.customer_name,
        "location_name": location.location_name,
        "market_id": location.market_id,
        "total_capacity_mbps": location.total_capacity_mbps,
        "allocated_mbps": location.allocated_mbps,
        "maintenance_buffer_mbps": location.maintenance_buffer_mbps,
        "available_mbps": available,
        "utilization_pct": utilization_pct(
            location.total_capacity_mbps,
            location.allocated_mbps,
            location.maintenance_buffer_mbps,
            policy,
        ),
        "can_support": available >= int(requested_mbps),
        "headroom_mbps": available - int(requested_mbps),
    }


def list_locations(
    locations: Iterable[Location],
    policy: InventoryPolicy,
    requested_mbps: int = 0,
    market_id: str | None = None,
    search: str | None = None,
) -> list[dict[str, Any]]:
    selected = list(locations)
    if market_id:
        selected = [loc for loc in selected if loc.market_id == market_id]
    if search:
        needle = search.lower()
        selected = [
            loc for loc in selected
            if needle in f"{loc.customer_name} {loc.location_name} {loc.location_code}".lower()
        ]
    return [enrich_location(loc, policy, requested_mbps) for loc in selected]
