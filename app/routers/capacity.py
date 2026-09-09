from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Query, Request
from fastapi.concurrency import run_in_threadpool
from fastapi.responses import HTMLResponse

from app.inventory.locations import (
    AVAILABILITY_RULE,
    buffer_total_mbps,
    get_location,
    list_locations,
)
from app.pagination import PageParams, paginate
from app.security import Principal, sales_principal
from app.templating import templates

router = APIRouter(tags=["capacity"])


@router.get("/capacity/locations")
async def get_locations(
    requested_mbps: int = Query(default=0, ge=0),
    market_id: str | None = Query(default=None),
    search: str | None = Query(default=None),
    page: PageParams = Depends(),  # noqa: B008
    principal: Principal = Depends(sales_principal),  # noqa: B008
):
    locations = await run_in_threadpool(
        list_locations, requested_mbps=requested_mbps, market_id=market_id, search=search
    )
    page_locations, pagination = paginate(locations, page.limit, page.offset)
    return {
        "rule": AVAILABILITY_RULE,
        "requested_mbps": requested_mbps,
        "count": len(locations),
        "serviceable_count": sum(1 for location in locations if location["can_support"]),
        "available_mbps": sum(location["available_mbps"] for location in locations),
        "maintenance_buffer_mbps": sum(
            location["maintenance_buffer_mbps"] for location in locations
        ),
        "locations": page_locations,
        "pagination": pagination,
    }


@router.get("/capacity/locations/{location_code}")
async def get_single_location(
    location_code: str,
    requested_mbps: int = Query(default=0, ge=0),
    principal: Principal = Depends(sales_principal),  # noqa: B008
):
    location = await run_in_threadpool(get_location, location_code, requested_mbps=requested_mbps)
    if location is None:
        raise HTTPException(status_code=404, detail="location not found")
    return location


@router.get("/capacity", response_class=HTMLResponse)
async def capacity_check(
    request: Request,
    requested_mbps: int = Query(default=350, ge=0),
    principal: Principal = Depends(sales_principal),  # noqa: B008
):
    locations = await run_in_threadpool(list_locations, requested_mbps=requested_mbps)
    buffer_total = await run_in_threadpool(buffer_total_mbps)
    return templates.TemplateResponse(
        request,
        "capacity.html",
        {
            "rule": AVAILABILITY_RULE,
            "requested": requested_mbps,
            "locations": locations,
            "markets": sorted({location["market_id"] for location in locations}),
            "location_count": len(locations),
            "serviceable": sum(1 for location in locations if location["can_support"]),
            "available": sum(location["available_mbps"] for location in locations),
            "buffer_total": buffer_total,
        },
    )
