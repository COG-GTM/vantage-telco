from __future__ import annotations

from decimal import Decimal
from typing import Any, Dict, List, Optional

from app.db import all_documents
import telco_rules

from app.billing.rules import PROFILE, to_money


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
    period = usage["period"]
    usage_mb = int(usage["usage_mb"])
    included_gb = int(account["included_gb"])
    shared_account = {
        "province": account.get("province", ""),
        "plan_monthly_fee": account.get("plan_monthly_fee", 0) or 0,
        "included_gb": included_gb,
        "previous_plan_fee": account.get("previous_plan_fee", 0) or 0,
        "plan_change_day": account.get("plan_change_day", 0) or 0,
        "line_count": account.get("line_count", 1) or 1,
        "promo_credit_amount": account.get("promo_credit_amount", 0) or 0,
        "promo_issued_on": account.get("promo_issued_on") or "",
        "suspension_start_day": account.get("suspension_start_day", 0) or 0,
        "suspension_end_day": account.get("suspension_end_day", 0) or 0,
        "prior_balance": account.get("prior_balance", 0) or 0,
        "prior_due_date": account.get("prior_due_date") or "",
        "loyalty_discount_pct": account.get("loyalty_discount_pct", 0) or 0,
    }
    shared = telco_rules.compute_invoice(PROFILE, shared_account, usage_mb, period)

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
        "usage_gb_rated": shared["usage_gb_rated"],
        "included_gb": included_gb,
        "overage_gb": shared["overage_gb"],
        "overage_mb": shared["overage_mb"],
        "plan_charge": to_money(shared["plan_charge"]),
        "line_discount": to_money(shared["line_discount"]),
        "recurring": to_money(shared["recurring"]),
        "overage_charges": to_money(shared["overage_charges"]),
        "suspension_credit": to_money(shared["suspension_credit"]),
        "promo_credit": to_money(shared["promo_credit"]),
        "late_fee": to_money(shared["late_fee"]),
        "subtotal": to_money(shared["subtotal"]),
        "loyalty_discount_pct": account.get("loyalty_discount_pct", 0) or 0,
        "loyalty_discount": to_money(shared["loyalty"]),
        "federal_tax_label": shared["federal_label"],
        "federal_tax": to_money(shared["federal_tax"]),
        "provincial_tax_label": shared["provincial_label"],
        "provincial_tax": to_money(shared["provincial_tax"]),
        "invoice_total": to_money(shared["total"]),
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
