from __future__ import annotations

from fastapi import APIRouter, Depends, Query
from fastapi.concurrency import run_in_threadpool

from app.network import addressing
from app.pagination import PageParams, paginate
from app.security import Principal, ops_principal

router = APIRouter(prefix="/network", tags=["network"])


@router.get("/addressing")
async def get_addressing(principal: Principal = Depends(ops_principal)):  # noqa: B008
    return await run_in_threadpool(addressing.summary)


@router.get("/devices")
async def get_devices(
    page: PageParams = Depends(),  # noqa: B008
    principal: Principal = Depends(ops_principal),  # noqa: B008
):
    devices = await run_in_threadpool(addressing.devices)
    page_devices, pagination = paginate(devices, page.limit, page.offset)
    return {"count": len(devices), "devices": page_devices, "pagination": pagination}


@router.get("/references")
async def get_references(
    address: str = Query(...),
    principal: Principal = Depends(ops_principal),  # noqa: B008
):
    hits = await run_in_threadpool(addressing.references, address)
    return {"address": address, "file_count": len(hits), "files": [str(p) for p in hits]}
