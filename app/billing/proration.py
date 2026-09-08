"""Shared 30-day proration for mid-cycle plan changes."""

from __future__ import annotations

from decimal import Decimal

from telco_billing_rules import prorated_plan_charge as _prorated_plan_charge


def prorated_plan_charge(
    monthly_fee: Decimal,
    previous_monthly_fee: Decimal,
    change_day: int,
    period: str | None = None,
) -> Decimal:
    """Return shared-rule proration; ``period`` is retained for call compatibility and ignored."""
    del period
    return _prorated_plan_charge(monthly_fee, previous_monthly_fee, change_day)
