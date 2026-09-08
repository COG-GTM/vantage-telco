"""Shared whole-gigabyte usage rating."""

from __future__ import annotations

from telco_billing_rules import money, overage_gb, rate_overage, usage_gb_rounded


def overage_mb(usage_mb: int, included_gb: int) -> int:
    """Return the raw excess megabytes as an informational value."""
    return max(int(usage_mb) - int(included_gb) * 1024, 0)
