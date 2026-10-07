"""Proration on a mid-cycle plan change, from telco-rules (DECISIONS.md D-05).

The billing month is 30 days whatever the calendar says; ``period`` is accepted
for call-site compatibility and does not change the result.
"""

from __future__ import annotations

from decimal import Decimal
from typing import Optional

import telco_rules

BILLING_MONTH_DAYS = telco_rules.BILLING_MONTH_DAYS


def daily_rate(monthly_fee: Decimal, period: Optional[str] = None) -> Decimal:
    return Decimal(str(telco_rules.daily_rate(float(monthly_fee))))


def prorated_plan_charge(
    monthly_fee: Decimal, previous_monthly_fee: Decimal, change_day: int, period: Optional[str] = None
) -> Decimal:
    return Decimal(
        str(telco_rules.prorated_plan_charge(float(monthly_fee), float(previous_monthly_fee), int(change_day or 0)))
    )
