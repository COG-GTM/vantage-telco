from __future__ import annotations

from decimal import Decimal
from typing import Any, Dict, List, Optional

from app.billing.discounts import loyalty_discount
from app.billing.latefee import late_fee
from app.billing.lines import multi_line_discount
from app.billing.promo import promo_credit
from app.billing.proration import prorated_plan_charge
from app.billing.rating import money, overage_mb, rate_overage
from app.billing.suspension import suspension_credit
from app.billing.tax import federal_tax, provincial_tax, rates_for_province
from app.db import all_documents


def accounts() -> List[Dict[str, Any]]:
    return all_documents("accounts")


def usage_records(account_id: Optional[str] = None, period: Optional[str] = None) -> List[Dict[str, Any]]:
    records = all_documents("usage")
    if account_id:
        records = [r for r in records if r.get("account_id") == account_id]
    if period:
        records = [r for r in records if r.get("period") == period]
    return records


def find_account(account_id: str) -> Optional[Dict[str, Any]]:
    for account in accounts():
        if account["account_id"] == account_id:
            return account
    return None


def build_invoice(account: Dict[str, Any], usage: Dict[str, Any]) -> Dict[str, Any]:
    """Assemble one invoice.

    Charges are carried at full precision and rounded once, at the total: the
    invoice is a single amount owed, not a stack of separately rounded lines.
    """
    period = usage["period"]
    usage_mb = int(usage["usage_mb"])
    included_gb = int(account["included_gb"])
    plan_fee = Decimal(str(account["plan_monthly_fee"]))

    plan_charge = prorated_plan_charge(
        plan_fee,
        Decimal(str(account.get("previous_plan_fee", 0) or 0)),
        int(account.get("plan_change_day", 0) or 0),
        period,
    )
    line_discount = multi_line_discount(plan_charge, int(account.get("line_count", 1) or 1))
    recurring = plan_charge - line_discount
    overage_charges = rate_overage(usage_mb, included_gb)
    credit = suspension_credit(
        plan_fee,
        int(account.get("suspension_start_day", 0) or 0),
        int(account.get("suspension_end_day", 0) or 0),
        period,
    )
    promo = promo_credit(
        Decimal(str(account.get("promo_credit_amount", 0) or 0)),
        account.get("promo_issued_on"),
        period,
    )
    fee = late_fee(Decimal(str(account.get("prior_balance", 0) or 0)), account.get("prior_due_date"), period)

    subtotal = max(recurring + overage_charges + fee - credit - promo, Decimal("0"))
    rates = rates_for_province(account.get("province", ""))
    loyalty = loyalty_discount(subtotal, account["loyalty_discount_pct"])
    federal = federal_tax(subtotal, rates)
    provincial = provincial_tax(subtotal, loyalty, rates)
    total = subtotal - loyalty + federal + provincial

    return {
        "account_id": account["account_id"],
        "billing_ref": account.get("billing_ref", ""),
        "legal_name": account["legal_name"],
        "tax_id": account["tax_id"],
        "service_address": account["service_address"],
        "province": account.get("province", ""),
        "plan_code": account.get("plan_code", ""),
        "period": period,
        "usage_mb": usage_mb,
        "included_gb": included_gb,
        "overage_mb": overage_mb(usage_mb, included_gb),
        "plan_charge": float(money(plan_charge)),
        "line_discount": float(money(line_discount)),
        "recurring": float(money(recurring)),
        "overage_charges": float(money(overage_charges)),
        "suspension_credit": float(money(credit)),
        "promo_credit": float(money(promo)),
        "late_fee": float(money(fee)),
        "subtotal": float(money(subtotal)),
        "loyalty_discount_pct": account["loyalty_discount_pct"],
        "loyalty_discount": float(money(loyalty)),
        "federal_tax_label": rates.federal_label,
        "federal_tax": float(money(federal)),
        "provincial_tax_label": rates.provincial_label,
        "provincial_tax": float(money(provincial)),
        "invoice_total": float(money(total)),
    }


def list_invoices(account_id: Optional[str] = None, period: Optional[str] = None) -> List[Dict[str, Any]]:
    invoices = []
    for usage in usage_records(account_id=account_id, period=period):
        if not usage.get("account_id"):
            # Usage with no billing account never reaches an invoice.
            continue
        account = find_account(usage["account_id"])
        if account is None:
            continue
        invoices.append(build_invoice(account, usage))
    return invoices


def unlinked_usage(period: Optional[str] = None) -> List[Dict[str, Any]]:
    """Mediated usage carrying no billing account. Never invoiced today."""
    records = [r for r in all_documents("usage") if not r.get("account_id")]
    if period:
        records = [r for r in records if r.get("period") == period]
    return records


def billed_usage_mb(period: Optional[str] = None) -> int:
    return sum(int(i["usage_mb"]) for i in list_invoices(period=period))


def mediated_usage_mb(period: Optional[str] = None) -> int:
    records = all_documents("usage")
    if period:
        records = [r for r in records if r.get("period") == period]
    return sum(int(r["usage_mb"]) for r in records)


def revenue_total(period: Optional[str] = None) -> Decimal:
    return sum((Decimal(str(i["invoice_total"])) for i in list_invoices(period=period)), Decimal("0"))
