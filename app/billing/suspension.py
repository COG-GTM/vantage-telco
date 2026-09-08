from __future__ import annotations

from decimal import Decimal

import telco_rules

from app.billing.rules import PROFILE, to_money


def suspended_days(start_day: int, end_day: int) -> int:
    return telco_rules.suspended_days(int(start_day), int(end_day))


def suspension_credit(
    monthly_fee: Decimal | int | float, start_day: int, end_day: int, period: str
) -> Decimal:
    return to_money(
        telco_rules.suspension_credit(
            PROFILE, float(monthly_fee), int(start_day), int(end_day), period
        )
    )
