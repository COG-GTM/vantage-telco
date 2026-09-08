from __future__ import annotations

from decimal import Decimal
from typing import Optional

import telco_rules

from app.billing.rules import PROFILE, to_money


def days_past_due(due_date: Optional[str], period: str) -> int:
    return telco_rules.days_past_due(due_date, period)


def late_fee(
    prior_balance: Decimal | int | float, due_date: Optional[str], period: str
) -> Decimal:
    return to_money(
        telco_rules.late_fee(PROFILE, float(prior_balance), due_date, period)
    )
