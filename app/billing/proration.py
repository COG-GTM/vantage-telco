"""Proration on a mid-cycle plan change.

A partial month is priced on the calendar: a day in February costs more than a
day in July, because the customer had the service for a larger share of the
cycle. There is no 30-day convention here.
"""

from __future__ import annotations

from calendar import monthrange
from decimal import Decimal


def days_in_period(period: str) -> int:
    year, month = (int(part) for part in period.split("-")[:2])
    return monthrange(year, month)[1]


def daily_rate(monthly_fee: Decimal, period: str) -> Decimal:
    return Decimal(monthly_fee) / Decimal(days_in_period(period))


def prorated_plan_charge(
    monthly_fee: Decimal, previous_monthly_fee: Decimal, change_day: int, period: str
) -> Decimal:
    total_days = days_in_period(period)
    if not change_day:
        return Decimal(monthly_fee)
    days_on_old = max(0, min(int(change_day) - 1, total_days))
    days_on_new = total_days - days_on_old
    return (
        daily_rate(previous_monthly_fee, period) * days_on_old
        + daily_rate(monthly_fee, period) * days_on_new
    )
