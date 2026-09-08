from decimal import Decimal

import telco_rules


PROFILE = telco_rules.meridian_profile()


def to_money(x: float) -> Decimal:
    return Decimal(f"{x:.2f}")
