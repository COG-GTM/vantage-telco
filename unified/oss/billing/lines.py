"""Multi-line discount off the recurring charge.

Both estates publish the same schedule, so the tiers are policy data rather
than a divergence: 3 to 9 lines 5%, 10 or more 10%.
"""

from __future__ import annotations

from decimal import Decimal

from oss.billing.money import line, pct_of
from oss.policy import BillingPolicy


def multi_line_pct(line_count: int, policy: BillingPolicy) -> Decimal:
    for threshold, pct in policy.multi_line_tiers:
        if int(line_count) >= threshold:
            return pct
    return Decimal("0")


def multi_line_discount(
    recurring_charge: Decimal, line_count: int, policy: BillingPolicy
) -> Decimal:
    return line(pct_of(recurring_charge, multi_line_pct(line_count, policy), policy), policy)
