from __future__ import annotations

from fastapi import APIRouter, HTTPException, Query, Request, Security
from fastapi.responses import HTMLResponse

from app import security
from app.inventory.locations import (
    AVAILABILITY_RULE,
    buffer_total_mbps,
    get_location,
    list_locations,
)
from app.templating import templates

router = APIRouter(
    tags=["capacity"],
    dependencies=[Security(security.require_scopes, scopes=[security.SCOPE_SALES_ENGINEERING])],
)

@router.get("/capacity/locations")
async def get_locations(
    requested_mbps: int = Query(default=0, ge=0),
    market_id: str | None = Query(default=None),
    search: str | None = Query(default=None),
):
    locations = list_locations(requested_mbps=requested_mbps, market_id=market_id, search=search)
    return {
        "rule": AVAILABILITY_RULE,
        "requested_mbps": requested_mbps,
        "count": len(locations),
        "serviceable_count": sum(1 for location in locations if location["can_support"]),
        "available_mbps": sum(location["available_mbps"] for location in locations),
        "maintenance_buffer_mbps": sum(
            location["maintenance_buffer_mbps"] for location in locations
        ),
        "locations": locations,
    }


@router.get("/capacity/locations/{location_code}")
async def get_single_location(location_code: str, requested_mbps: int = Query(default=0, ge=0)):
    location = get_location(location_code, requested_mbps=requested_mbps)
    if location is None:
        raise HTTPException(status_code=404, detail="location not found")
    return location


@router.get("/capacity", response_class=HTMLResponse)
async def capacity_check(
    request: Request,
    requested_mbps: int = Query(default=350, ge=0),
):
    locations = list_locations(requested_mbps=requested_mbps)
    markets = sorted({location["market_id"] for location in locations})
    return templates.TemplateResponse(
        request,
        "capacity.html",
        {
            "rule": AVAILABILITY_RULE,
            "requested": requested_mbps,
            "markets": markets,
            "locations": locations,
            "serviceable": sum(1 for location in locations if location["can_support"]),
            "available": sum(location["available_mbps"] for location in locations),
            "buffer_total": buffer_total_mbps(),
        },
    )
