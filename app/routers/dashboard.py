from __future__ import annotations

from fastapi import APIRouter, Request, Security
from fastapi.responses import HTMLResponse

from app import security
from app.billing import invoices as invoice_service
from app.inventory import circuits as circuit_rules
from app.inventory.repository import list_circuits, list_sites
from app.templating import templates

router = APIRouter(
    tags=["dashboard"],
    dependencies=[
        Security(
            security.require_scopes,
            scopes=[security.SCOPE_NOC, security.SCOPE_BILLING_OPS],
        )
    ],
)


@router.get("/dashboard", response_class=HTMLResponse)
async def dashboard(
    request: Request,
    period: str = "2026-07",
    principal: security.Principal = Security(  # noqa: B008
        security.require_scopes,
        scopes=[security.SCOPE_NOC, security.SCOPE_BILLING_OPS],
    ),
):
    sites = list_sites()
    circuits = list_circuits()
    invoices = [
        security.redact_pii(invoice, principal)
        for invoice in invoice_service.list_invoices(period=period)
    ]
    unlinked = invoice_service.unlinked_usage(period=period)
    return templates.TemplateResponse(
        request,
        "dashboard.html",
        {
            "sites": sites,
            "active_circuits": circuit_rules.active_count(circuits),
            "invoices": invoices,
            "unlinked": unlinked,
            "revenue": invoice_service.revenue_total(period=period),
            "period": period,
        },
    )


@router.get("/dashboard/billing", response_class=HTMLResponse)
async def billing_dashboard(
    request: Request,
    period: str = "2026-07",
    account_id: str = "",
    billing_ref: str = "",
    principal: security.Principal = Security(  # noqa: B008
        security.require_scopes,
        scopes=[security.SCOPE_NOC, security.SCOPE_BILLING_OPS],
    ),
):
    """Invoice register on its own, filterable down to a single account."""
    invoices = [
        security.redact_pii(invoice, principal)
        for invoice in invoice_service.list_invoices(
            period=period, account_id=account_id or None
        )
    ]
    if billing_ref:
        invoices = [i for i in invoices if i["billing_ref"] == billing_ref]
    return templates.TemplateResponse(
        request,
        "dashboard_billing.html",
        {
            "invoices": invoices,
            "revenue": sum(i["invoice_total"] for i in invoices),
            "period": period,
            "account_id": account_id,
            "billing_ref": billing_ref,
        },
    )
