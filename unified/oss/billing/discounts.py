"""Loyalty credit.

Both services take the credit off the subtotal; what differs is what it does to
the tax base (see ``oss/billing/tax.py``). The archived NOC report takes the
same credit after tax instead, which is why the stage is a policy option.
"""

from __future__ import annotations

from decimal import Decimal

from oss.billing.money import line, pct_of
from oss.policy import BillingPolicy, LoyaltyStage


def loyalty_discount(amount: Decimal, loyalty_pct: Decimal, policy: BillingPolicy) -> Decimal:
    return line(pct_of(amount, loyalty_pct, policy), policy)


def credit_base(subtotal: Decimal, taxes: Decimal, policy: BillingPolicy) -> Decimal:
    """The amount the loyalty percentage is taken from."""
    if policy.loyalty_stage is LoyaltyStage.POST_TAX:
        return Decimal(subtotal) + Decimal(taxes)
    return Decimal(subtotal)
