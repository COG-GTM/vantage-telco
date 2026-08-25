"""Proration on a mid-cycle plan change.

Meridian prices a partial month against a fixed 30-day billing month, whatever
the calendar says, because the downstream reconciliation reports assume it.
Vantage prices it against the actual days in the cycle, so a day in February
costs more than a day in July.
"""

from __future__ import annotations

from calendar import monthrange
from decimal import Decimal

from oss.billing.money import divide, line, multiply
from oss.policy import BillingPolicy, ProrationBasis


def days_in_period(period: str, policy: BillingPolicy) -> int:
    if policy.proration_basis is ProrationBasis.THIRTY_DAY:
        return policy.billing_month_days
    year, month = (int(part) for part in period.split("-")[:2])
    return monthrange(year, month)[1]


def daily_rate(monthly_fee: Decimal, period: str, policy: BillingPolicy) -> Decimal:
    return divide(monthly_fee, days_in_period(period, policy), policy)


def prorated_plan_charge(
    monthly_fee: Decimal,
    previous_monthly_fee: Decimal,
    change_day: int,
    period: str,
    policy: BillingPolicy,
) -> Decimal:
    if not change_day:
        return line(Decimal(monthly_fee), policy)
    total_days = days_in_period(period, policy)
    days_on_old = max(0, min(int(change_day) - 1, total_days))
    days_on_new = total_days - days_on_old
    old_rate = daily_rate(previous_monthly_fee, period, policy)
    new_rate = daily_rate(monthly_fee, period, policy)
    old_part = line(multiply(old_rate, days_on_old, policy), policy)
    new_part = line(multiply(new_rate, days_on_new, policy), policy)
    return line(old_part + new_part, policy)
