"""Suspension and reactivation inside a cycle.

A suspended line carries no traffic, so the customer is credited the days it
was suspended at the plan's daily rate.
"""

from __future__ import annotations

from calendar import monthrange
from decimal import Decimal


def days_in_period(period: str) -> int:
    year, month = (int(part) for part in period.split("-")[:2])
    return monthrange(year, month)[1]


def daily_rate(monthly_fee: Decimal, period: str) -> Decimal:
    return Decimal(monthly_fee) / Decimal(days_in_period(period))


def suspended_days(start_day: int, end_day: int) -> int:
    if not start_day or end_day < start_day:
        return 0
    return int(end_day) - int(start_day) + 1


def suspension_credit(monthly_fee: Decimal, start_day: int, end_day: int, period: str) -> Decimal:
    days = suspended_days(start_day, end_day)
    if not days:
        return Decimal("0")
    return daily_rate(Decimal(monthly_fee), period) * days
