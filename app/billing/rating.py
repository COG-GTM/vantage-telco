from __future__ import annotations

from decimal import Decimal

import telco_rules

from app.billing.rules import PROFILE, to_money


def usage_gb_rounded(usage_mb: int) -> int:
    return telco_rules.usage_gb_rounded(int(usage_mb))


def overage_mb(usage_mb: int, included_gb: int) -> int:
    return telco_rules.overage_mb(int(usage_mb), int(included_gb))


def overage_gb(usage_mb: int, included_gb: int) -> int:
    return telco_rules.overage_gb(int(usage_mb), int(included_gb))


def rate_overage(usage_mb: int, included_gb: int) -> Decimal:
    return to_money(telco_rules.rate_overage(PROFILE, int(usage_mb), int(included_gb)))


def money(amount: Decimal | int | float) -> Decimal:
    return to_money(float(amount))
