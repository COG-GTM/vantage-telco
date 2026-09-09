from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Query

from app.billing import invoices as invoice_service
from app.security import Principal, ops_principal, redact_invoices

router = APIRouter(prefix="/billing", tags=["billing"])


@router.get("/invoices")
def get_invoices(
    account_id: str | None = Query(default=None),
    period: str | None = Query(default=None),
    principal: Principal = Depends(ops_principal),  # noqa: B008
):
    found = invoice_service.list_invoices(account_id=account_id, period=period)
    if account_id and not found:
        raise HTTPException(status_code=404, detail="no invoices for account")
    return {
        "count": len(found),
        "revenue_total": float(invoice_service.revenue_total(period=period)),
        "invoices": redact_invoices(found, principal),
    }


@router.get("/usage-summary")
def get_usage_summary(
    period: str | None = Query(default=None),
    principal: Principal = Depends(ops_principal),  # noqa: B008
):
    mediated = invoice_service.mediated_usage_mb(period=period)
    billed = invoice_service.billed_usage_mb(period=period)
    return {
        "period": period,
        "mediated_usage_mb": mediated,
        "billed_usage_mb": billed,
        "unbilled_usage_mb": mediated - billed,
        "unlinked_usage_records": invoice_service.unlinked_usage(period=period),
    }
