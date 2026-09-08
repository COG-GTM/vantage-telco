from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal
from typing import Dict

import telco_rules

from app.billing.rules import PROFILE, to_money


@dataclass(frozen=True)
class TaxRates:
    federal_pct: Decimal
    provincial_pct: Decimal
    federal_label: str
    provincial_label: str


PROVINCE_RATES: Dict[str, TaxRates] = {}
for _province in ("BC", "AB", "ON", "QC"):
    _rates = telco_rules.rates_for_province(_province)
    PROVINCE_RATES[_province] = TaxRates(
        Decimal(str(_rates.federal_pct)),
        Decimal(str(_rates.provincial_pct)),
        _rates.federal_label,
        _rates.provincial_label,
    )
_rates = telco_rules.rates_for_province("")
DEFAULT_RATES = TaxRates(
    Decimal(str(_rates.federal_pct)),
    Decimal(str(_rates.provincial_pct)),
    _rates.federal_label,
    _rates.provincial_label,
)


def rates_for_province(province: str) -> TaxRates:
    return PROVINCE_RATES.get((province or "").upper(), DEFAULT_RATES)


def _shared_rates(rates: TaxRates) -> telco_rules.TaxRates:
    return telco_rules.TaxRates(
        float(rates.federal_pct),
        float(rates.provincial_pct),
        rates.federal_label,
        rates.provincial_label,
    )


def federal_tax(
    pre_discount_amount: Decimal | int | float, rates: TaxRates
) -> Decimal:
    return to_money(
        telco_rules.federal_tax(
            PROFILE, float(pre_discount_amount), _shared_rates(rates)
        )
    )


def provincial_tax(
    pre_discount_amount: Decimal | int | float,
    discount: Decimal | int | float,
    rates: TaxRates,
) -> Decimal:
    return to_money(
        telco_rules.provincial_tax(
            PROFILE,
            float(pre_discount_amount),
            float(discount),
            _shared_rates(rates),
        )
    )
