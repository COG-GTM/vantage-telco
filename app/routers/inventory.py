from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.concurrency import run_in_threadpool

from app.inventory import circuits as circuit_rules
from app.inventory.repository import get_site, list_circuits, list_sites
from app.pagination import PageParams, paginate
from app.security import Principal, ops_principal

router = APIRouter(tags=["inventory"])


@router.get("/resources")
async def get_resources(
    market_id: str | None = Query(default=None),
    lifecycle_state: str | None = Query(default=None),
    page: PageParams = Depends(),  # noqa: B008
    principal: Principal = Depends(ops_principal),  # noqa: B008
):
    sites = await run_in_threadpool(
        list_sites, market_id=market_id, lifecycle_state=lifecycle_state
    )
    resources, pagination = paginate(sites, page.limit, page.offset)
    return {"count": len(sites), "resources": resources, "pagination": pagination}


@router.get("/resources/{device_uuid}")
async def get_resource(
    device_uuid: str,
    principal: Principal = Depends(ops_principal),  # noqa: B008
):
    site = await run_in_threadpool(get_site, device_uuid)
    if site is None:
        raise HTTPException(status_code=404, detail="resource not found")
    return site


@router.get("/circuits")
async def get_circuits(
    circuit_id: str | None = Query(default=None),
    page: PageParams = Depends(),  # noqa: B008
    principal: Principal = Depends(ops_principal),  # noqa: B008
):
    found = await run_in_threadpool(list_circuits, circuit_id=circuit_id)
    circuits, pagination = paginate(found, page.limit, page.offset)
    return {
        "count": len(found),
        "active_count": circuit_rules.active_count(found),
        "active_capacity_mbps": circuit_rules.active_capacity_mbps(found),
        "circuits": circuits,
        "pagination": pagination,
    }
