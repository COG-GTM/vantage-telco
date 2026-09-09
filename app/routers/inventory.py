from __future__ import annotations

from fastapi import APIRouter, HTTPException, Query, Security

from app import security
from app.inventory import circuits as circuit_rules
from app.inventory.repository import get_site, list_circuits, list_sites
from app.pagination import PageDep

router = APIRouter(
    tags=["inventory"],
    dependencies=[
        Security(
            security.require_scopes,
            scopes=[security.SCOPE_INVENTORY_READ, security.SCOPE_NOC],
        )
    ],
)


@router.get("/resources")
async def get_resources(
    page: PageDep,
    market_id: str | None = Query(default=None),
    lifecycle_state: str | None = Query(default=None),
):
    sites = list_sites(market_id=market_id, lifecycle_state=lifecycle_state)
    return page.envelope(sites)


@router.get("/resources/{device_uuid}")
async def get_resource(device_uuid: str):
    site = get_site(device_uuid)
    if site is None:
        raise HTTPException(status_code=404, detail="resource not found")
    return site


@router.get("/circuits")
async def get_circuits(
    page: PageDep,
    circuit_id: str | None = Query(default=None),
):
    found = list_circuits(circuit_id=circuit_id)
    return page.envelope(
        found,
        active_count=circuit_rules.active_count(found),
        active_capacity_mbps=circuit_rules.active_capacity_mbps(found),
    )
