"""The billing rules, re-exported from the shared library.

Every rate, threshold and formula lives in COG-GTM/telco-billing-rules, vendored
into ``vendor/`` and shared with the meridian estate so the two registers cannot
disagree. Nothing in this package implements a rule of its own; a rule change
belongs upstream, followed by ``python tools/vendor.py --python vendor``.
"""

from __future__ import annotations

import sys
from pathlib import Path

_VENDOR = Path(__file__).resolve().parents[2] / "vendor" / "python"
if str(_VENDOR) not in sys.path:
    sys.path.insert(0, str(_VENDOR))

from billing_rules import (  # noqa: E402
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
    suspended_days,
    suspension_credit,
    usage_gb_rounded,
)

__all__ = [
    "InvoiceAmounts",
    "InvoiceInputs",
    "TaxRates",
    "apply_loyalty",
    "billing_days_in_period",
    "compute_invoice_amounts",
    "daily_rate",
    "days_past_due",
    "federal_tax",
    "late_fee",
    "loyalty_discount",
    "money",
    "multi_line_discount",
    "multi_line_pct",
    "overage_gb",
    "overage_mb",
    "promo_credit",
    "promo_is_live",
    "prorated_plan_charge",
    "provincial_tax",
    "rate_overage",
    "rates_for_province",
    "suspended_days",
    "suspension_credit",
    "usage_gb_rounded",
]
