from __future__ import annotations

from fastapi import APIRouter, Depends, Request
from fastapi.concurrency import run_in_threadpool
from fastapi.responses import HTMLResponse

from app.billing import invoices as invoice_service
from app.inventory import circuits as circuit_rules
from app.inventory.repository import list_circuits, list_sites
from app.security import Principal, ops_principal, redact_invoices
from app.templating import templates

router = APIRouter(tags=["dashboard"])


@router.get("/dashboard", response_class=HTMLResponse)
async def dashboard(
    request: Request,
    period: str = "2026-07",
    principal: Principal = Depends(ops_principal),  # noqa: B008
):
    sites = await run_in_threadpool(list_sites)
    circuits = await run_in_threadpool(list_circuits)
    invoices = await run_in_threadpool(invoice_service.list_invoices, period=period)
    unlinked = await run_in_threadpool(invoice_service.unlinked_usage, period=period)
    revenue = await run_in_threadpool(invoice_service.revenue_total, period=period)
    return templates.TemplateResponse(
        request,
        "dashboard.html",
        {
            "period": period,
            "sites": sites,
            "circuits": circuits,
            "invoices": redact_invoices(invoices, principal),
            "unlinked": unlinked,
            "revenue": revenue,
            "active_circuits": circuit_rules.active_count(circuits),
        },
    )


@router.get("/dashboard/billing", response_class=HTMLResponse)
async def billing_dashboard(
    request: Request,
    period: str = "2026-07",
    account_id: str = "",
    billing_ref: str = "",
    principal: Principal = Depends(ops_principal),  # noqa: B008
):
    """Invoice register on its own, filterable down to a single account."""
    invoices = await run_in_threadpool(
        invoice_service.list_invoices, period=period, account_id=account_id or None
    )
    if billing_ref:
        invoices = [invoice for invoice in invoices if invoice["billing_ref"] == billing_ref]
    invoices = redact_invoices(invoices, principal)
    return templates.TemplateResponse(
        request,
        "billing_dashboard.html",
        {
            "period": period,
            "account_id": account_id,
            "billing_ref": billing_ref,
            "invoices": invoices,
            "revenue": sum(invoice["invoice_total"] for invoice in invoices),
        },
    )
