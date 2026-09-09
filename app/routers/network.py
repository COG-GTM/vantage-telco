from __future__ import annotations

from fastapi import APIRouter, Depends, Query

from app.network import addressing
from app.security import Principal, ops_principal

router = APIRouter(prefix="/network", tags=["network"])


@router.get("/addressing")
def get_addressing(principal: Principal = Depends(ops_principal)):  # noqa: B008
    return addressing.summary()


@router.get("/devices")
def get_devices(principal: Principal = Depends(ops_principal)):  # noqa: B008
    devices = addressing.devices()
    return {"count": len(devices), "devices": devices}


@router.get("/references")
def get_references(
    address: str = Query(...),
    principal: Principal = Depends(ops_principal),  # noqa: B008
):
    hits = addressing.references(address)
    return {"address": address, "file_count": len(hits), "files": [str(p) for p in hits]}
