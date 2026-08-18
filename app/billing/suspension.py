"""Suspension and reactivation inside a cycle.

A suspended line carries no traffic, so the customer is credited the days it
was suspended at the plan's daily rate.
"""

from __future__ import annotations

from decimal import Decimal

from app.billing.proration import daily_rate


def suspended_days(start_day: int, end_day: int) -> int:
    if not start_day or end_day < start_day:
        return 0
    return int(end_day) - int(start_day) + 1


def suspension_credit(monthly_fee: Decimal, start_day: int, end_day: int, period: str) -> Decimal:
    days = suspended_days(start_day, end_day)
    if not days:
        return Decimal("0")
    return daily_rate(Decimal(monthly_fee), period) * days
