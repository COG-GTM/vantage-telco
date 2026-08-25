"""Canadian sales tax.

Both estates agree that GST/HST sits on the charge before any loyalty credit:
the CRA treats the credit as goodwill, not a reduction of consideration.

They disagree on the provincial component. Meridian assesses PST/QST on what
the customer actually pays, so the loyalty credit comes off the base first.
Vantage taxes what was invoiced, so PST/QST sit on the same pre-discount
subtotal as the federal line.
"""

from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal

from oss.billing.money import line, pct_of
from oss.policy import BillingPolicy, TaxBase


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


def _base(subtotal: Decimal, discount: Decimal, basis: TaxBase) -> Decimal:
    if basis is TaxBase.PRE_DISCOUNT:
        return Decimal(subtotal)
    return max(Decimal(subtotal) - Decimal(discount), Decimal("0"))


def federal_tax(
    subtotal: Decimal, discount: Decimal, rates: TaxRates, policy: BillingPolicy
) -> Decimal:
    base = _base(subtotal, discount, policy.federal_tax_base)
    return line(pct_of(base, rates.federal_pct, policy), policy)


def provincial_tax(
    subtotal: Decimal, discount: Decimal, rates: TaxRates, policy: BillingPolicy
) -> Decimal:
    if rates.provincial_pct == 0:
        return Decimal("0")
    base = _base(subtotal, discount, policy.provincial_tax_base)
    return line(pct_of(base, rates.provincial_pct, policy), policy)
