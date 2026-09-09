"""Serviceable customer locations.

Sales engineers use this to answer one question: can we sell the customer the
bandwidth they are asking for at this location today? The answer uses the same
capacity rule as the rest of the platform — the maintenance buffer is withheld,
because capacity reserved for maintenance windows is not sellable.
"""

from __future__ import annotations

from typing import Any

from app.db import all_documents
from app.inventory.capacity import available_capacity, utilization_pct

AVAILABILITY_RULE = "available = total_capacity - allocated - maintenance_buffer"


def enrich_location(location: dict[str, Any], requested_mbps: int = 0) -> dict[str, Any]:
    total = int(location["total_capacity_mbps"])
    allocated = int(location["allocated_mbps"])
    buffer_mbps = int(location["maintenance_buffer_mbps"])
    available = available_capacity(total, allocated, buffer_mbps)
    enriched = dict(location)
    enriched.update(
        available_mbps=available,
        utilization_pct=utilization_pct(total, allocated, buffer_mbps),
        can_support=available >= requested_mbps,
        headroom_mbps=available - requested_mbps,
    )
    return enriched


def list_locations(
    requested_mbps: int = 0,
    market_id: str | None = None,
    search: str | None = None,
) -> list[dict[str, Any]]:
    locations = all_documents("locations")
    if market_id:
        locations = [location for location in locations if location["market_id"] == market_id]
    if search:
        needle = search.lower()
        locations = [
            location
            for location in locations
            if needle
            in (
                f"{location['customer_name']} "
                f"{location['location_name']} "
                f"{location['location_code']}"
            ).lower()
        ]
    return [enrich_location(location, requested_mbps) for location in locations]


def get_location(location_code: str, requested_mbps: int = 0) -> dict[str, Any] | None:
    for location in all_documents("locations"):
        if location["location_code"] == location_code:
            return enrich_location(location, requested_mbps)
    return None


def buffer_total_mbps() -> int:
    return sum(
        int(location["maintenance_buffer_mbps"]) for location in all_documents("locations")
    )
