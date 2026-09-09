from __future__ import annotations

from fastapi import APIRouter, Query, Security

from app import security
from app.network import addressing
from app.pagination import PageDep

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
async def get_addressing():
    return addressing.summary()


@router.get("/devices")
async def get_devices(page: PageDep):
    devices = addressing.devices()
    return page.envelope(devices)


@router.get("/references")
async def get_references(page: PageDep, address: str = Query(...)):
    hits = addressing.references(address)
    return page.envelope([str(p) for p in hits], address=address)
