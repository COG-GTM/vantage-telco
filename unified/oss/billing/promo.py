"""Promotional credits.

Meridian treats the billing cycle as the unit: a credit issued in June is a
June credit and does not roll into July. Vantage keeps a credit live for a
fixed window of days from issue, so a credit issued late in a month is still
live in the next one.
"""

from __future__ import annotations

from datetime import date, timedelta
from decimal import Decimal

from oss.billing.money import line
from oss.policy import BillingPolicy, PromoExpiry


def parse_date(value: str | None) -> date | None:
    if not value:
        return None
    try:
        return date.fromisoformat(value)
    except ValueError:
        return None


def period_start(period: str) -> date:
    year, month = (int(part) for part in period.split("-")[:2])
    return date(year, month, 1)


def promo_is_live(issued_on: str | None, period: str, policy: BillingPolicy) -> bool:
    issued = parse_date(issued_on)
    if issued is None:
        return False
    cycle = period_start(period)
    if policy.promo_expiry is PromoExpiry.ISSUE_CYCLE:
        return (issued.year, issued.month) == (cycle.year, cycle.month)
    return issued + timedelta(days=policy.promo_valid_days) >= cycle


def promo_credit(
    amount: Decimal, issued_on: str | None, period: str, policy: BillingPolicy
) -> Decimal:
    amount = Decimal(amount)
    if amount <= 0 or not promo_is_live(issued_on, period, policy):
        return Decimal("0")
    return line(amount, policy)
