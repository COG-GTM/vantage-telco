"""Usage rating, from the shared telco-rules library (DECISIONS.md D-01).

Usage is rated in whole gigabytes, partial gigabytes round up, at a flat $10/GB
over the plan allowance.
"""

from __future__ import annotations

from decimal import ROUND_HALF_UP, Decimal

import telco_rules

MB_PER_GB = telco_rules.MB_PER_GB
OVERAGE_RATE_PER_GB = Decimal(str(telco_rules.OVERAGE_RATE_PER_GB))


def overage_mb(usage_mb: int, included_gb: int) -> int:
    """Measured megabytes over the allowance (informational, not the rated quantity)."""
    return max(usage_mb - included_gb * MB_PER_GB, 0)


def usage_gb_rated(usage_mb: int) -> int:
    return telco_rules.usage_gb_rounded(usage_mb)


def overage_gb(usage_mb: int, included_gb: int) -> int:
    return telco_rules.overage_gb(usage_mb, included_gb)


def rate_overage(usage_mb: int, included_gb: int) -> Decimal:
    return money(Decimal(str(telco_rules.rate_overage(usage_mb, included_gb))))


def money(amount: Decimal) -> Decimal:
    return Decimal(amount).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
