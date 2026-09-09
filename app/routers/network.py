from __future__ import annotations

from fastapi import APIRouter, Query, Security

from app import security
from app.network import addressing

router = APIRouter(
    prefix="/network",
    tags=["network"],
    dependencies=[
        Security(
            security.require_scopes,
            scopes=[security.SCOPE_NETWORK_READ, security.SCOPE_NOC],
        )
    ],
)


@router.get("/addressing")
def get_addressing():
    return addressing.summary()


@router.get("/devices")
def get_devices():
    devices = addressing.devices()
    return {"count": len(devices), "devices": devices}


@router.get("/references")
def get_references(address: str = Query(...)):
    hits = addressing.references(address)
    return {"address": address, "file_count": len(hits), "files": [str(p) for p in hits]}
