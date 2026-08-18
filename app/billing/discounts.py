"""Loyalty credit.

The loyalty discount comes off the subtotal. It does not change the base the
tax is assessed on — see ``app/billing/tax.py``.
"""

from __future__ import annotations

from decimal import Decimal

from app.billing.rating import money


def loyalty_discount(amount: Decimal, loyalty_pct: float) -> Decimal:
    return Decimal(amount) * Decimal(str(loyalty_pct)) / Decimal(100)


def apply_loyalty(amount: Decimal, loyalty_pct: float) -> Decimal:
    return money(Decimal(amount) - loyalty_discount(amount, loyalty_pct))
