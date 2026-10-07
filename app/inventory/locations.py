"""Serviceable customer locations.

Sales engineers use this to answer one question: can we sell the customer the
bandwidth they are asking for at this location today? The answer uses the shared
telco-rules capacity rule (DECISIONS.md D-07): available = total - allocated,
and the location can take the request when available >= requested. The
maintenance buffer on the record is reported but not withheld.
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional

from app.db import all_documents
from app.inventory.capacity import available_capacity, can_support, utilization_pct

AVAILABILITY_RULE = "available = total_capacity - allocated"


def enrich_location(location: Dict[str, Any], requested_mbps: int = 0) -> Dict[str, Any]:
    total = int(location["total_capacity_mbps"])
    allocated = int(location["allocated_mbps"])
    available = available_capacity(total, allocated)
    enriched = dict(location)
    enriched.update(
        available_mbps=available,
        utilization_pct=utilization_pct(total, allocated),
        can_support=can_support(total, allocated, requested_mbps),
        headroom_mbps=available - requested_mbps,
    )
    return enriched


def list_locations(
    requested_mbps: int = 0,
    market_id: Optional[str] = None,
    search: Optional[str] = None,
) -> List[Dict[str, Any]]:
    locations = all_documents("locations")
    if market_id:
        locations = [l for l in locations if l["market_id"] == market_id]
    if search:
        needle = search.lower()
        locations = [
            l for l in locations
            if needle in f"{l['customer_name']} {l['location_name']} {l['location_code']}".lower()
        ]
    return [enrich_location(l, requested_mbps) for l in locations]


def get_location(location_code: str, requested_mbps: int = 0) -> Optional[Dict[str, Any]]:
    for location in all_documents("locations"):
        if location["location_code"] == location_code:
            return enrich_location(location, requested_mbps)
    return None


def buffer_total_mbps() -> int:
    return sum(int(l["maintenance_buffer_mbps"]) for l in all_documents("locations"))
