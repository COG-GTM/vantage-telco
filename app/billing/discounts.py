"""Loyalty credit, from telco-rules.

The loyalty discount comes off the subtotal, and the provincial tax is assessed
after it — see ``app/billing/tax.py``.
"""

from __future__ import annotations

from decimal import Decimal

import telco_rules


def loyalty_discount(amount: Decimal, loyalty_pct: float) -> Decimal:
    return Decimal(str(telco_rules.loyalty_discount(float(amount), float(loyalty_pct))))


def apply_loyalty(amount: Decimal, loyalty_pct: float) -> Decimal:
    return Decimal(str(telco_rules.apply_loyalty(float(amount), float(loyalty_pct))))
