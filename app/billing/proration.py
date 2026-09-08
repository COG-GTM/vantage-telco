from __future__ import annotations

from decimal import Decimal

import telco_rules

from app.billing.rules import PROFILE, to_money


def days_in_period(period: str) -> int:
    return telco_rules.days_in_period(PROFILE, period)


def daily_rate(monthly_fee: Decimal | int | float, period: str) -> Decimal:
    return to_money(telco_rules.daily_rate(PROFILE, float(monthly_fee), period))


def prorated_plan_charge(
    monthly_fee: Decimal | int | float,
    previous_monthly_fee: Decimal | int | float,
    change_day: int,
    period: str,
) -> Decimal:
    return to_money(
        telco_rules.prorated_plan_charge(
            PROFILE,
            float(monthly_fee),
            float(previous_monthly_fee),
            int(change_day),
            period,
        )
    )
