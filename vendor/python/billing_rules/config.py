"""generated from rules.json by tools/generate.py -- do not edit by hand"""

from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal
from typing import Dict, Tuple

SPEC_VERSION = 1
DEFAULT_PROFILE = "meridian"

LINE_ROUNDING_PER_LINE = True

BILLING_MONTH_DAYS = 30
PRORATION_CALENDAR_MONTH = False

MB_PER_GB = 1024
OVERAGE_RATE_PER_GB = Decimal("10.0")
OVERAGE_RATE_PER_MB = Decimal("0.012")
RATING_EXACT_MB = False

PROMO_VALID_DAYS = 30
PROMO_EXPIRY_ROLLING_DAYS = False

SUSPENSION_CREDIT_DAILY_RATE = False

LATE_FEE_GRACE_DAYS = 10
LATE_FEE_PCT = Decimal("1.5")

PROVINCIAL_TAX_POST_DISCOUNT = True

LINE_TIERS: Tuple[Tuple[int, Decimal], ...] = ((10, Decimal("10.0")), (3, Decimal("5.0")),)


@dataclass(frozen=True)
class ProvinceRates:
    federal_pct: Decimal
    provincial_pct: Decimal
    federal_label: str
    provincial_label: str


PROVINCE_RATES: Dict[str, ProvinceRates] = {
    "BC": ProvinceRates(Decimal("5.0"), Decimal("7.0"), "GST", "PST"),
    "AB": ProvinceRates(Decimal("5.0"), Decimal("0.0"), "GST", ""),
    "ON": ProvinceRates(Decimal("13.0"), Decimal("0.0"), "HST", ""),
    "QC": ProvinceRates(Decimal("5.0"), Decimal("9.975"), "GST", "QST"),
}

DEFAULT_RATES = ProvinceRates(Decimal("5.0"), Decimal("0.0"), "GST", "")
