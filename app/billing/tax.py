"""Canadian sales tax, from telco-rules (DECISIONS.md D-03).

GST (and HST in the harmonized provinces) is assessed on the charge before any
loyalty discount. PST and QST are assessed on what the customer pays, after the
loyalty discount.
"""

from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal

import telco_rules


@dataclass(frozen=True)
class TaxRates:
    federal_pct: Decimal
    provincial_pct: Decimal
    federal_label: str
    provincial_label: str


def rates_for_province(province: str) -> TaxRates:
    rates = telco_rules.rates_for_province((province or "").upper())
    return TaxRates(
        Decimal(str(rates.federal_pct)),
        Decimal(str(rates.provincial_pct)),
        rates.federal_label,
        rates.provincial_label,
    )


def _native(rates: TaxRates) -> telco_rules.TaxRates:
    return telco_rules.TaxRates(
        float(rates.federal_pct), float(rates.provincial_pct), rates.federal_label, rates.provincial_label
    )


def federal_tax(pre_discount_amount: Decimal, rates: TaxRates) -> Decimal:
    return Decimal(str(telco_rules.federal_tax(float(pre_discount_amount), _native(rates))))


def provincial_tax(pre_discount_amount: Decimal, discount: Decimal, rates: TaxRates) -> Decimal:
    return Decimal(str(telco_rules.provincial_tax(float(pre_discount_amount), float(discount), _native(rates))))
