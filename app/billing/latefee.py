"""Late fee on a balance carried into the next cycle, from telco-rules.

Ten days of grace after the due date, then 1.5% of whatever is still
outstanding when the cycle opens.
"""

from __future__ import annotations

from decimal import Decimal
from typing import Optional

import telco_rules

GRACE_DAYS = telco_rules.LATE_FEE_GRACE_DAYS
LATE_FEE_PCT = Decimal(str(telco_rules.LATE_FEE_PCT))


def days_past_due(due_date: Optional[str], period: str) -> int:
    return telco_rules.days_past_due(due_date or "", period)


def late_fee(prior_balance: Decimal, due_date: Optional[str], period: str) -> Decimal:
    return Decimal(str(telco_rules.late_fee(float(prior_balance), due_date or "", period)))
