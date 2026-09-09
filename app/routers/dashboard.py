from __future__ import annotations

import html

from fastapi import APIRouter, Depends
from fastapi.responses import HTMLResponse

from app.billing import invoices as invoice_service
from app.inventory import circuits as circuit_rules
from app.inventory.repository import list_circuits, list_sites
from app.security import Principal, ops_principal, redact_invoices

router = APIRouter(tags=["dashboard"])

STYLE = """
body { font-family: 'Segoe UI', Helvetica, Arial, sans-serif; margin: 0; background: #f7f9fc; color: #14213d; }
header { background: #0f766e; color: #fff; padding: 18px 28px; }
header h1 { margin: 0; font-size: 20px; font-weight: 600; }
main { padding: 24px 28px; }
.tiles { display: flex; gap: 16px; flex-wrap: wrap; margin-bottom: 24px; }
.tile { background: #fff; border-radius: 10px; box-shadow: 0 1px 3px rgba(20,33,61,.12); padding: 16px 20px; min-width: 170px; }
.tile .n { font-size: 28px; font-weight: 600; }
.tile .l { color: #64748b; font-size: 12px; text-transform: uppercase; letter-spacing: .06em; }
table { border-collapse: collapse; width: 100%; background: #fff; border-radius: 10px; overflow: hidden; box-shadow: 0 1px 3px rgba(20,33,61,.12); margin-bottom: 28px; }
th { text-align: left; background: #e2e8f0; padding: 8px 12px; font-size: 12px; }
td { padding: 7px 12px; border-top: 1px solid #f1f5f9; font-size: 13px; }
td.num { text-align: right; }
h2 { font-size: 15px; margin: 22px 0 10px; }
"""


def _tax_cell(invoice: dict) -> str:
    parts = [f"{html.escape(str(invoice['federal_tax_label']))} ${invoice['federal_tax']:.2f}"]
    if invoice["provincial_tax_label"]:
        parts.append(
            f"{html.escape(str(invoice['provincial_tax_label']))} ${invoice['provincial_tax']:.2f}"
        )
    return " + ".join(parts)


@router.get("/dashboard", response_class=HTMLResponse)
def dashboard(
    period: str = "2026-07",
    principal: Principal = Depends(ops_principal),  # noqa: B008
):
    e = html.escape
    sites = list_sites()
    circuits = list_circuits()
    invoices = redact_invoices(invoice_service.list_invoices(period=period), principal)
    unlinked = invoice_service.unlinked_usage(period=period)
    revenue = invoice_service.revenue_total(period=period)

    site_rows = "".join(
        f"<tr><td>{e(str(s['name']))}</td><td>{e(str(s['market_id']))}</td>"
        f"<td>{e(str(s['lifecycle_state']))}</td>"
        f"<td>{e(str(s.get('tower_registration', '')))}</td>"
        f"<td class='num'>{s['total_capacity_mbps']}</td>"
        f"<td class='num'>{s['allocated_mbps']}</td><td class='num'>{s['maintenance_buffer_mbps']}</td>"
        f"<td class='num'>{s['available_mbps']}</td></tr>"
        for s in sites
    )
    invoice_rows = "".join(
        f"<tr><td>{e(str(i['account_id']))}</td><td>{e(str(i['legal_name']))}</td>"
        f"<td>{e(str(i['province']))}</td>"
        f"<td class='num'>{i['usage_mb']}</td><td class='num'>{i['overage_mb']}</td>"
        f"<td class='num'>${i['recurring']:.2f}</td><td class='num'>${i['overage_charges']:.2f}</td>"
        f"<td class='num'>${i['subtotal']:.2f}</td><td class='num'>-${i['loyalty_discount']:.2f}</td>"
        f"<td class='num'>{_tax_cell(i)}</td><td class='num'>${i['invoice_total']:.2f}</td></tr>"
        for i in invoices
    )
    unlinked_rows = "".join(
        f"<tr><td>{e(str(u['usage_id']))}</td><td>{e(str(u['device_uuid']))}</td>"
        f"<td>{e(str(u['period']))}</td>"
        f"<td class='num'>{u['usage_mb']}</td><td>no billing account</td></tr>"
        for u in unlinked
    )
    escaped_period = e(period)

    return f"""<!DOCTYPE html>
<html><head><meta charset="utf-8"><title>Vantage Net</title><style>{STYLE}</style></head>
<body>
<header><h1>Vantage Net &middot; Inventory &amp; Billing</h1></header>
<main>
  <div class="tiles">
    <div class="tile"><div class="n">{len(sites)}</div><div class="l">Resources</div></div>
    <div class="tile"><div class="n">{sum(1 for s in sites if s["lifecycle_state"] == "ACTIVE")}</div><div class="l">Active</div></div>
    <div class="tile"><div class="n">{circuit_rules.active_count(circuits)}</div><div class="l">Active circuits</div></div>
    <div class="tile"><div class="n">${revenue:,.2f}</div><div class="l">Billed revenue {escaped_period}</div></div>
    <div class="tile"><div class="n">{sum(int(u["usage_mb"]) for u in unlinked):,}</div><div class="l">Unbilled MB {escaped_period}</div></div>
  </div>
  <h2>Invoices &middot; {escaped_period}</h2>
  <table><thead><tr><th>Account</th><th>Customer</th><th>Province</th><th>Usage MB</th><th>Overage MB</th>
  <th>Recurring</th><th>Overage</th><th>Subtotal</th><th>Loyalty</th><th>Tax</th><th>Total</th></tr></thead>
  <tbody>{invoice_rows}</tbody></table>
  <h2>Mediated usage with no invoice</h2>
  <table><thead><tr><th>Usage ID</th><th>Device</th><th>Period</th><th>Usage MB</th><th>Reason</th></tr></thead>
  <tbody>{unlinked_rows}</tbody></table>
  <h2>Resources</h2>
  <table><thead><tr><th>Name</th><th>Market</th><th>Lifecycle</th><th>Tower reg</th><th>Total</th><th>Allocated</th><th>Buffer</th><th>Available</th></tr></thead>
  <tbody>{site_rows}</tbody></table>
</main></body></html>"""


@router.get("/dashboard/billing", response_class=HTMLResponse)
def billing_dashboard(
    period: str = "2026-07",
    account_id: str = "",
    billing_ref: str = "",
    principal: Principal = Depends(ops_principal),  # noqa: B008
):
    """Invoice register on its own, filterable down to a single account."""
    invoices = invoice_service.list_invoices(period=period, account_id=account_id or None)
    if billing_ref:
        invoices = [i for i in invoices if i["billing_ref"] == billing_ref]
    invoices = redact_invoices(invoices, principal)
    revenue = sum(i["invoice_total"] for i in invoices)
    e = html.escape
    escaped_period = e(period)
    escaped_account_id = e(account_id)
    escaped_billing_ref = e(billing_ref)

    rows = "".join(
        f"<tr><td>{e(str(i['account_id']))}</td><td>{e(str(i['billing_ref']))}</td>"
        f"<td>{e(str(i['legal_name']))}</td>"
        f"<td>{e(str(i['province']))}</td><td class='num'>{i['usage_mb']}</td>"
        f"<td class='num'>{i['overage_mb']}</td>"
        f"<td class='num'>${i['recurring']:.2f}</td><td class='num'>${i['overage_charges']:.2f}</td>"
        f"<td class='num'>-${i['promo_credit']:.2f}</td><td class='num'>-${i['suspension_credit']:.2f}</td>"
        f"<td class='num'>${i['late_fee']:.2f}</td><td class='num'>${i['subtotal']:.2f}</td>"
        f"<td class='num'>-${i['loyalty_discount']:.2f}</td><td class='num'>{_tax_cell(i)}</td>"
        f"<td class='num'>${i['invoice_total']:.2f}</td></tr>"
        for i in invoices
    )

    return f"""<!DOCTYPE html>
<html><head><meta charset="utf-8"><title>Vantage Net &middot; Billing</title><style>{STYLE}</style></head>
<body>
<header><h1>Vantage Net &middot; Invoice Register</h1></header>
<main>
  <form method="get" action="/dashboard/billing">
    <label>Period <input name="period" value="{escaped_period}"></label>
    <label>Account <input name="account_id" value="{escaped_account_id}" placeholder="VANTAGE-BILL-..."></label>
    <label>Billing ref <input name="billing_ref" value="{escaped_billing_ref}" placeholder="TN-0001"></label>
    <button type="submit">Show</button>
  </form>
  <div class="tiles">
    <div class="tile"><div class="n">{len(invoices)}</div><div class="l">Invoices {escaped_period}</div></div>
    <div class="tile"><div class="n">${revenue:,.2f}</div><div class="l">Billed revenue</div></div>
  </div>
  <table><thead><tr><th>Account</th><th>Ref</th><th>Customer</th><th>Province</th><th>Usage MB</th>
  <th>Overage MB</th><th>Recurring</th><th>Overage</th><th>Promo</th><th>Suspension</th><th>Late fee</th>
  <th>Subtotal</th><th>Loyalty</th><th>Tax</th><th>Total</th></tr></thead>
  <tbody>{rows}</tbody></table>
</main></body></html>"""
