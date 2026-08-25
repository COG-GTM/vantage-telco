"""Invoice assembly.

One code path for every estate. The rules that differ are read off the policy,
so a Meridian invoice and a Vantage invoice are the same computation with
different options, and ``rules`` records which options produced the numbers.
"""

from __future__ import annotations

from decimal import Decimal
from typing import Any

from oss.billing.discounts import credit_base, loyalty_discount
from oss.billing.latefee import late_fee
from oss.billing.lines import multi_line_discount
from oss.billing.money import line, money
from oss.billing.promo import promo_credit
from oss.billing.proration import prorated_plan_charge
from oss.billing.rating import overage_gb, overage_mb, rate_overage
from oss.billing.suspension import suspension_credit
from oss.billing.tax import federal_tax, provincial_tax, rates_for_province
from oss.model import Account, Invoice, UsageRecord
from oss.policy import BillingPolicy, EstatePolicy, LoyaltyStage


def rule_summary(policy: BillingPolicy) -> dict[str, Any]:
    return {
        "rating_basis": policy.rating_basis.value,
        "overage_rate": str(policy.overage_rate),
        "proration_basis": policy.proration_basis.value,
        "promo_expiry": policy.promo_expiry.value,
        "suspension_credit": policy.suspension_credit.value,
        "federal_tax_base": policy.federal_tax_base.value,
        "provincial_tax_base": policy.provincial_tax_base.value,
        "loyalty_stage": policy.loyalty_stage.value,
        "rounding": policy.rounding.value,
    }


def compute_invoice(account: Account, usage: UsageRecord, estate: EstatePolicy) -> Invoice:
    policy = estate.billing
    period = usage.period
    usage_mb = int(usage.usage_mb)
    included_gb = int(account.included_gb)

    plan_charge = prorated_plan_charge(
        account.plan_monthly_fee,
        account.previous_plan_fee,
        account.plan_change_day,
        period,
        policy,
    )
    line_discount = multi_line_discount(plan_charge, account.line_count, policy)
    recurring = line(plan_charge - line_discount, policy)
    overage_charges = rate_overage(usage_mb, included_gb, policy)
    credit = suspension_credit(
        account.plan_monthly_fee,
        account.suspension_start_day,
        account.suspension_end_day,
        period,
        policy,
    )
    promo = promo_credit(account.promo_credit_amount, account.promo_issued_on, period, policy)
    fee = late_fee(account.prior_balance, account.prior_due_date, period, policy)

    subtotal = line(
        max(recurring + overage_charges + fee - credit - promo, Decimal("0")), policy
    )

    rates = rates_for_province(account.province)
    if policy.loyalty_stage is LoyaltyStage.POST_TAX:
        federal = federal_tax(subtotal, Decimal("0"), rates, policy)
        provincial = provincial_tax(subtotal, Decimal("0"), rates, policy)
        loyalty = loyalty_discount(
            credit_base(subtotal, federal + provincial, policy),
            account.loyalty_discount_pct,
            policy,
        )
    else:
        loyalty = loyalty_discount(subtotal, account.loyalty_discount_pct, policy)
        federal = federal_tax(subtotal, loyalty, rates, policy)
        provincial = provincial_tax(subtotal, loyalty, rates, policy)

    total = line(subtotal - loyalty + federal + provincial, policy)

    return Invoice(
        account_id=account.account_id,
        billing_ref=account.billing_ref,
        period=period,
        province=account.province,
        estate=estate.name,
        legal_name=account.legal_name,
        usage_mb=usage_mb,
        included_gb=included_gb,
        overage_mb=overage_mb(usage_mb, included_gb),
        overage_gb=overage_gb(usage_mb, included_gb),
        plan_charge=money(plan_charge),
        line_discount=money(line_discount),
        recurring=money(recurring),
        overage_charges=money(overage_charges),
        suspension_credit=money(credit),
        promo_credit=money(promo),
        late_fee=money(fee),
        subtotal=money(subtotal),
        loyalty_discount=money(loyalty),
        federal_tax_label=rates.federal_label,
        federal_tax=money(federal),
        provincial_tax_label=rates.provincial_label,
        provincial_tax=money(provincial),
        total=money(total),
        rules=rule_summary(policy),
    )


def invoice_dict(invoice: Invoice) -> dict[str, Any]:
    out: dict[str, Any] = {}
    for key, value in invoice.__dict__.items():
        out[key] = float(value) if isinstance(value, Decimal) else value
    return out
