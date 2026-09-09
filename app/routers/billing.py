from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.concurrency import run_in_threadpool

from app.billing import invoices as invoice_service
from app.pagination import PageParams, paginate
from app.security import Principal, ops_principal, redact_invoices

router = APIRouter(prefix="/billing", tags=["billing"])


@router.get("/invoices")
async def get_invoices(
    account_id: str | None = Query(default=None),
    period: str | None = Query(default=None),
    page: PageParams = Depends(),  # noqa: B008
    principal: Principal = Depends(ops_principal),  # noqa: B008
):
    found = await run_in_threadpool(
        invoice_service.list_invoices, account_id=account_id, period=period
    )
    if account_id and not found:
        raise HTTPException(status_code=404, detail="no invoices for account")
    invoices, pagination = paginate(found, page.limit, page.offset)
    revenue_total = await run_in_threadpool(invoice_service.revenue_total, period=period)
    return {
        "count": len(found),
        "revenue_total": float(revenue_total),
        "invoices": redact_invoices(invoices, principal),
        "pagination": pagination,
    }


@router.get("/usage-summary")
async def get_usage_summary(
    period: str | None = Query(default=None),
    principal: Principal = Depends(ops_principal),  # noqa: B008
):
    mediated = await run_in_threadpool(invoice_service.mediated_usage_mb, period=period)
    billed = await run_in_threadpool(invoice_service.billed_usage_mb, period=period)
    unlinked = await run_in_threadpool(invoice_service.unlinked_usage, period=period)
    return {
        "period": period,
        "mediated_usage_mb": mediated,
        "billed_usage_mb": billed,
        "unbilled_usage_mb": mediated - billed,
        "unlinked_usage_records": unlinked,
    }
