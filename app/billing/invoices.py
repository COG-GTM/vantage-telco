from __future__ import annotations

from decimal import Decimal
from typing import Any, Dict, List, Optional

from app.billing.rules import InvoiceInputs, compute_invoice_amounts
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

    Every amount comes from the shared rules library; this function only maps our
    documents onto its inputs and its result onto the invoice payload.
    """
    period = usage["period"]
    usage_mb = int(usage["usage_mb"])
    included_gb = int(account["included_gb"])

    amounts = compute_invoice_amounts(
        InvoiceInputs(
            period=period,
            province=account.get("province", ""),
            usage_mb=usage_mb,
            included_gb=included_gb,
            plan_fee=Decimal(str(account["plan_monthly_fee"])),
            previous_plan_fee=Decimal(str(account.get("previous_plan_fee", 0) or 0)),
            plan_change_day=int(account.get("plan_change_day", 0) or 0),
            line_count=int(account.get("line_count", 1) or 1),
            promo_amount=Decimal(str(account.get("promo_credit_amount", 0) or 0)),
            promo_issued_on=account.get("promo_issued_on"),
            suspension_start_day=int(account.get("suspension_start_day", 0) or 0),
            suspension_end_day=int(account.get("suspension_end_day", 0) or 0),
            prior_balance=Decimal(str(account.get("prior_balance", 0) or 0)),
            prior_due_date=account.get("prior_due_date"),
            loyalty_pct=account["loyalty_discount_pct"],
        )
    )

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
        "usage_gb_rated": amounts.usage_gb_rated,
        "overage_gb": amounts.overage_gb,
        "overage_mb": amounts.overage_mb,
        "plan_charge": float(amounts.plan_charge),
        "line_discount": float(amounts.line_discount),
        "recurring": float(amounts.recurring),
        "overage_charges": float(amounts.overage_charges),
        "suspension_credit": float(amounts.suspension_credit),
        "promo_credit": float(amounts.promo_credit),
        "late_fee": float(amounts.late_fee),
        "subtotal": float(amounts.subtotal),
        "loyalty_discount_pct": account["loyalty_discount_pct"],
        "loyalty_discount": float(amounts.loyalty_discount),
        "federal_tax_label": amounts.federal_label,
        "federal_tax": float(amounts.federal_tax),
        "provincial_tax_label": amounts.provincial_label,
        "provincial_tax": float(amounts.provincial_tax),
        "invoice_total": float(amounts.total),
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
