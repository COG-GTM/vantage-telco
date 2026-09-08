from __future__ import annotations

from decimal import Decimal

import telco_rules

from app.billing.rules import PROFILE, to_money


def loyalty_discount(
    amount: Decimal | int | float, loyalty_pct: Decimal | int | float
) -> Decimal:
    return to_money(
        telco_rules.loyalty_discount(
            PROFILE, float(amount), float(loyalty_pct)
        )
    )


def apply_loyalty(
    amount: Decimal | int | float, loyalty_pct: Decimal | int | float
) -> Decimal:
    return to_money(float(amount) - float(loyalty_discount(amount, loyalty_pct)))
