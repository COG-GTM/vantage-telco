"""Late fee on a balance carried into the next cycle.

Ten days of grace after the due date, then 1.5% of whatever is still
outstanding when the cycle opens.
"""

from __future__ import annotations

from datetime import date
from decimal import Decimal
from typing import Optional

GRACE_DAYS = 10
LATE_FEE_PCT = Decimal("1.5")


def _parse(value: Optional[str]) -> Optional[date]:
    if not value:
        return None
    return date.fromisoformat(value)


def days_past_due(due_date: Optional[str], period: str) -> int:
    due = _parse(due_date)
    if due is None:
        return 0
    year, month = (int(part) for part in period.split("-")[:2])
    return max((date(year, month, 1) - due).days, 0)


def late_fee(prior_balance: Decimal, due_date: Optional[str], period: str) -> Decimal:
    balance = Decimal(prior_balance)
    if balance <= 0 or days_past_due(due_date, period) <= GRACE_DAYS:
        return Decimal("0")
    return balance * LATE_FEE_PCT / Decimal(100)
