from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Query

from app.inventory import circuits as circuit_rules
from app.inventory.repository import get_site, list_circuits, list_sites
from app.security import Principal, ops_principal

router = APIRouter(tags=["inventory"])


@router.get("/resources")
def get_resources(
    market_id: str | None = Query(default=None),
    lifecycle_state: str | None = Query(default=None),
    principal: Principal = Depends(ops_principal),  # noqa: B008
):
    sites = list_sites(market_id=market_id, lifecycle_state=lifecycle_state)
    return {"count": len(sites), "resources": sites}


@router.get("/resources/{device_uuid}")
def get_resource(
    device_uuid: str,
    principal: Principal = Depends(ops_principal),  # noqa: B008
):
    site = get_site(device_uuid)
    if site is None:
        raise HTTPException(status_code=404, detail="resource not found")
    return site


@router.get("/circuits")
def get_circuits(
    circuit_id: str | None = Query(default=None),
    principal: Principal = Depends(ops_principal),  # noqa: B008
):
    found = list_circuits(circuit_id=circuit_id)
    return {
        "count": len(found),
        "active_count": circuit_rules.active_count(found),
        "active_capacity_mbps": circuit_rules.active_capacity_mbps(found),
        "circuits": found,
    }
