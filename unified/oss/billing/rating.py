"""Usage rating.

Meridian bills whole gigabytes with partial gigabytes rounded up, at a flat
rate per gigabyte. Vantage bills the exact megabyte at a per-megabyte rate, so
a customer is never charged for a gigabyte they did not use.
"""

from __future__ import annotations

from decimal import Decimal

from oss.billing.money import money
from oss.policy import BillingPolicy, RatingBasis

MB_PER_GB = 1024


def usage_gb_rounded(usage_mb: int) -> int:
    gb, remainder = divmod(int(usage_mb), MB_PER_GB)
    return gb + 1 if remainder else gb


def overage_gb(usage_mb: int, included_gb: int) -> int:
    return max(usage_gb_rounded(usage_mb) - int(included_gb), 0)


def overage_mb(usage_mb: int, included_gb: int) -> int:
    return max(int(usage_mb) - int(included_gb) * MB_PER_GB, 0)


def rated_units(usage_mb: int, included_gb: int, policy: BillingPolicy) -> int:
    if policy.rating_basis is RatingBasis.WHOLE_GB:
        return overage_gb(usage_mb, included_gb)
    return overage_mb(usage_mb, included_gb)


def rate_overage(usage_mb: int, included_gb: int, policy: BillingPolicy) -> Decimal:
    # The overage line is rounded on both estates before it reaches the subtotal.
    return money(Decimal(rated_units(usage_mb, included_gb, policy)) * policy.overage_rate)
