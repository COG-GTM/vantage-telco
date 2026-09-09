from __future__ import annotations

from fastapi import APIRouter, HTTPException, Query

from app.billing import invoices as invoice_service

router = APIRouter(prefix="/billing", tags=["billing"])


@router.get("/invoices")
def get_invoices(
    account_id: str | None = Query(default=None),
    period: str | None = Query(default=None),
):
    found = invoice_service.list_invoices(account_id=account_id, period=period)
    if account_id and not found:
        raise HTTPException(status_code=404, detail="no invoices for account")
    return {
        "count": len(found),
        "revenue_total": float(invoice_service.revenue_total(period=period)),
        "invoices": found,
    }


@router.get("/usage-summary")
def get_usage_summary(period: str | None = Query(default=None)):
    mediated = invoice_service.mediated_usage_mb(period=period)
    billed = invoice_service.billed_usage_mb(period=period)
    return {
        "period": period,
        "mediated_usage_mb": mediated,
        "billed_usage_mb": billed,
        "unbilled_usage_mb": mediated - billed,
        "unlinked_usage_records": invoice_service.unlinked_usage(period=period),
    }
