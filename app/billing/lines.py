from __future__ import annotations

from decimal import Decimal

import telco_rules

from app.billing.rules import PROFILE, to_money


def multi_line_pct(line_count: int) -> Decimal:
    return to_money(telco_rules.multi_line_pct(int(line_count)))


def multi_line_discount(
    recurring_charge: Decimal | int | float, line_count: int
) -> Decimal:
    return to_money(
        telco_rules.multi_line_discount(
            PROFILE, float(recurring_charge), int(line_count)
        )
    )
