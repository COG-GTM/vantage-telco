"""Promotional credits.

A promo credit is live for 30 days from the day it was issued, whatever cycle
that lands in: a credit issued on the 24th of a month is still live on the 1st
of the next one.
"""

from __future__ import annotations

from datetime import date, timedelta
from decimal import Decimal

PROMO_VALID_DAYS = 30


def _parse(value: str | None) -> date | None:
    if not value:
        return None
    return date.fromisoformat(value)


def period_start(period: str) -> date:
    year, month = (int(part) for part in period.split("-")[:2])
    return date(year, month, 1)


def promo_is_live(issued_on: str | None, period: str) -> bool:
    issued = _parse(issued_on)
    if issued is None:
        return False
    return issued + timedelta(days=PROMO_VALID_DAYS) >= period_start(period)


def promo_credit(amount: Decimal, issued_on: str | None, period: str) -> Decimal:
    amount = Decimal(amount)
    if amount <= 0 or not promo_is_live(issued_on, period):
        return Decimal("0")
    return amount
