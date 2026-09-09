"""Canadian sales tax.

GST (and HST in the harmonized provinces) is assessed on the charge before any
loyalty discount: the discount is a goodwill credit, not a reduction of the
consideration.

The provincial component is assessed the same way. Vantage taxes what was
invoiced, not what was collected, so PST and QST also sit on the pre-discount
subtotal. Rate changes are a config change, not a code change.
"""

from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal


@dataclass(frozen=True)
class TaxRates:
    federal_pct: Decimal
    provincial_pct: Decimal
    federal_label: str
    provincial_label: str


PROVINCE_RATES: dict[str, TaxRates] = {
    "BC": TaxRates(Decimal("5"), Decimal("7"), "GST", "PST"),
    "AB": TaxRates(Decimal("5"), Decimal("0"), "GST", ""),
    "ON": TaxRates(Decimal("13"), Decimal("0"), "HST", ""),
    "QC": TaxRates(Decimal("5"), Decimal("9.975"), "GST", "QST"),
}

DEFAULT_RATES = TaxRates(Decimal("5"), Decimal("0"), "GST", "")


def rates_for_province(province: str) -> TaxRates:
    return PROVINCE_RATES.get((province or "").upper(), DEFAULT_RATES)


def federal_tax(pre_discount_amount: Decimal, rates: TaxRates) -> Decimal:
    return Decimal(pre_discount_amount) * rates.federal_pct / Decimal(100)


def provincial_tax(pre_discount_amount: Decimal, discount: Decimal, rates: TaxRates) -> Decimal:
    """PST/QST on the invoiced amount; the loyalty credit does not reduce it."""
    del discount
    if rates.provincial_pct == 0:
        return Decimal("0")
    return Decimal(pre_discount_amount) * rates.provincial_pct / Decimal(100)
