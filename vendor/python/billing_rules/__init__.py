"""Shared billing rules for meridian-telco and vantage-telco."""

from billing_rules.config import SPEC_VERSION
from billing_rules.rules import (  # noqa: F401
    InvoiceAmounts,
    InvoiceInputs,
    TaxRates,
    apply_loyalty,
    billing_days_in_period,
    compute_invoice_amounts,
    daily_rate,
    days_past_due,
    federal_tax,
    late_fee,
    loyalty_discount,
    money,
    multi_line_discount,
    multi_line_pct,
    overage_gb,
    overage_mb,
    promo_credit,
    promo_is_live,
    prorated_plan_charge,
    provincial_tax,
    rate_overage,
    rates_for_province,
    rounds_per_line,
    suspended_days,
    suspension_credit,
    usage_gb_rounded,
)

__all__ = ["SPEC_VERSION"] + [name for name in dir() if not name.startswith("_")]
