"""Estate policies.

Meridian and Vantage bill the same customer book and model the same network,
but a handful of rules genuinely differ between them. Every one of those rules
lives here as an explicit option instead of being hard-coded in two codebases,
so one engine can serve both estates and the differences are inspectable.
"""

from __future__ import annotations

from dataclasses import dataclass, replace
from decimal import Decimal
from enum import Enum


class RatingBasis(str, Enum):
    WHOLE_GB = "whole_gb"
    EXACT_MB = "exact_mb"


class ProrationBasis(str, Enum):
    THIRTY_DAY = "thirty_day"
    CALENDAR = "calendar"


class PromoExpiry(str, Enum):
    ISSUE_CYCLE = "issue_cycle"
    FIXED_WINDOW = "fixed_window"


class SuspensionCredit(str, Enum):
    NONE = "none"
    DAILY_RATE = "daily_rate"


class TaxBase(str, Enum):
    PRE_DISCOUNT = "pre_discount"
    POST_DISCOUNT = "post_discount"


class LoyaltyStage(str, Enum):
    SUBTOTAL = "subtotal"
    POST_TAX = "post_tax"


class Rounding(str, Enum):
    PER_LINE = "per_line"
    AT_TOTAL = "at_total"


class Arithmetic(str, Enum):
    BINARY64 = "binary64"
    DECIMAL = "decimal"


@dataclass(frozen=True)
class BillingPolicy:
    rating_basis: RatingBasis
    overage_rate: Decimal
    proration_basis: ProrationBasis
    billing_month_days: int
    promo_expiry: PromoExpiry
    promo_valid_days: int
    suspension_credit: SuspensionCredit
    federal_tax_base: TaxBase
    provincial_tax_base: TaxBase
    loyalty_stage: LoyaltyStage
    rounding: Rounding
    arithmetic: Arithmetic
    multi_line_tiers: tuple[tuple[int, Decimal], ...]
    late_fee_grace_days: int
    late_fee_pct: Decimal


@dataclass(frozen=True)
class InventoryPolicy:
    withhold_maintenance_buffer: bool
    active_circuit_roles: frozenset[str] | None


@dataclass(frozen=True)
class EstatePolicy:
    name: str
    billing: BillingPolicy
    inventory: InventoryPolicy


# 3-9 lines 5% off recurring, 10 or more 10%. Both estates publish this schedule.
MULTI_LINE_TIERS: tuple[tuple[int, Decimal], ...] = ((10, Decimal("10")), (3, Decimal("5")))

MERIDIAN = EstatePolicy(
    name="meridian",
    billing=BillingPolicy(
        rating_basis=RatingBasis.WHOLE_GB,
        overage_rate=Decimal("10.00"),
        proration_basis=ProrationBasis.THIRTY_DAY,
        billing_month_days=30,
        promo_expiry=PromoExpiry.ISSUE_CYCLE,
        promo_valid_days=0,
        suspension_credit=SuspensionCredit.NONE,
        federal_tax_base=TaxBase.PRE_DISCOUNT,
        provincial_tax_base=TaxBase.POST_DISCOUNT,
        loyalty_stage=LoyaltyStage.SUBTOTAL,
        rounding=Rounding.PER_LINE,
        arithmetic=Arithmetic.BINARY64,
        multi_line_tiers=MULTI_LINE_TIERS,
        late_fee_grace_days=10,
        late_fee_pct=Decimal("1.5"),
    ),
    inventory=InventoryPolicy(
        withhold_maintenance_buffer=False,
        active_circuit_roles=None,
    ),
)

VANTAGE = EstatePolicy(
    name="vantage",
    billing=BillingPolicy(
        rating_basis=RatingBasis.EXACT_MB,
        overage_rate=Decimal("0.012"),
        proration_basis=ProrationBasis.CALENDAR,
        billing_month_days=0,
        promo_expiry=PromoExpiry.FIXED_WINDOW,
        promo_valid_days=30,
        suspension_credit=SuspensionCredit.DAILY_RATE,
        federal_tax_base=TaxBase.PRE_DISCOUNT,
        provincial_tax_base=TaxBase.PRE_DISCOUNT,
        loyalty_stage=LoyaltyStage.SUBTOTAL,
        rounding=Rounding.AT_TOTAL,
        arithmetic=Arithmetic.DECIMAL,
        multi_line_tiers=MULTI_LINE_TIERS,
        late_fee_grace_days=10,
        late_fee_pct=Decimal("1.5"),
    ),
    inventory=InventoryPolicy(
        withhold_maintenance_buffer=True,
        active_circuit_roles=frozenset({"PRIMARY"}),
    ),
)

# The archived NOC report (java/vantage-report) rates like Vantage but takes the
# loyalty credit after tax rather than off the subtotal.
VANTAGE_REPORT = EstatePolicy(
    name="vantage-report",
    billing=replace(VANTAGE.billing, loyalty_stage=LoyaltyStage.POST_TAX),
    inventory=VANTAGE.inventory,
)

ESTATES: dict[str, EstatePolicy] = {p.name: p for p in (MERIDIAN, VANTAGE, VANTAGE_REPORT)}


def estate(name: str) -> EstatePolicy:
    try:
        return ESTATES[name]
    except KeyError:
        raise KeyError(f"unknown estate {name!r}, expected one of {sorted(ESTATES)}") from None
