"""Suspension inside a cycle.

A suspended Meridian line keeps its number, its provisioning and its place on
the switch, so the month is billed in full and nothing is credited. Vantage
credits the suspended days back at the plan's daily rate.
"""

from __future__ import annotations

from decimal import Decimal

from oss.billing.money import line, multiply
from oss.billing.proration import daily_rate
from oss.policy import BillingPolicy, SuspensionCredit


def suspended_days(start_day: int, end_day: int) -> int:
    if not start_day or int(end_day) < int(start_day):
        return 0
    return int(end_day) - int(start_day) + 1


def suspension_credit(
    monthly_fee: Decimal, start_day: int, end_day: int, period: str, policy: BillingPolicy
) -> Decimal:
    days = suspended_days(start_day, end_day)
    if not days or policy.suspension_credit is SuspensionCredit.NONE:
        return Decimal("0")
    return line(multiply(daily_rate(monthly_fee, period, policy), days, policy), policy)
