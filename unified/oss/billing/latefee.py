"""Late fee on a balance carried into the next cycle.

Both estates use the same rule — ten days of grace after the due date, then a
percentage of whatever is still outstanding when the cycle opens — so grace and
rate are policy data, not a divergence.
"""

from __future__ import annotations

from decimal import Decimal

from oss.billing.money import line, pct_of
from oss.billing.promo import parse_date, period_start
from oss.policy import BillingPolicy


def days_past_due(due_date: str | None, period: str) -> int:
    due = parse_date(due_date)
    if due is None:
        return 0
    return max((period_start(period) - due).days, 0)


def late_fee(
    prior_balance: Decimal, due_date: str | None, period: str, policy: BillingPolicy
) -> Decimal:
    balance = Decimal(prior_balance)
    if balance <= 0 or days_past_due(due_date, period) <= policy.late_fee_grace_days:
        return Decimal("0")
    return line(pct_of(balance, policy.late_fee_pct, policy), policy)
