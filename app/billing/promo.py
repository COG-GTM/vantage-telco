from __future__ import annotations

from decimal import Decimal
from typing import Optional

import telco_rules

from app.billing.rules import PROFILE, to_money


def promo_is_live(issued_on: Optional[str], period: str) -> bool:
    return telco_rules.promo_is_live(PROFILE, issued_on, period)


def promo_credit(
    amount: Decimal | int | float, issued_on: Optional[str], period: str
) -> Decimal:
    return to_money(telco_rules.promo_credit(PROFILE, float(amount), issued_on, period))
