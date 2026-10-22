"""Shared Canadian billing rules.

One implementation of every rule, mirrored by the C++ binding in ``cpp/``.
Behaviour is driven by the profile in ``rules.json``; the default profile is the
meridian one:

* proration on a fixed 30-day billing month
* usage rated in whole gigabytes, partial gigabytes rounding up, $10/GB overage
* promo credits live only in the cycle they were issued in
* a suspended line is billed the full month, no credit
* GST/HST on the pre-discount subtotal, PST/QST on the post-loyalty amount
* every charge line rounded to cents as it is produced
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date, timedelta
from decimal import ROUND_HALF_UP, Decimal
from typing import Optional

from billing_rules import config

__all__ = [
    "TaxRates",
    "InvoiceInputs",
    "InvoiceAmounts",
    "money",
    "rounds_per_line",
    "billing_days_in_period",
    "daily_rate",
    "prorated_plan_charge",
    "usage_gb_rounded",
    "overage_gb",
    "overage_mb",
    "rate_overage",
    "promo_is_live",
    "promo_credit",
    "suspended_days",
    "suspension_credit",
    "multi_line_pct",
    "multi_line_discount",
    "days_past_due",
    "late_fee",
    "rates_for_province",
    "federal_tax",
    "provincial_tax",
    "loyalty_discount",
    "apply_loyalty",
    "compute_invoice_amounts",
]

TaxRates = config.ProvinceRates

CENTS = Decimal("0.01")


# money ---------------------------------------------------------------------


def money(amount: Decimal) -> Decimal:
    """Half-up to cents."""
    return Decimal(amount).quantize(CENTS, rounding=ROUND_HALF_UP)


def rounds_per_line() -> bool:
    return config.LINE_ROUNDING_PER_LINE


def _line(amount: Decimal) -> Decimal:
    """Round a charge line if the profile rounds per line."""
    return money(amount) if config.LINE_ROUNDING_PER_LINE else Decimal(amount)


def _parse(value: Optional[str]) -> Optional[date]:
    if not value:
        return None
    try:
        return date.fromisoformat(value[:10])
    except ValueError:
        return None


def period_start(period: str) -> Optional[date]:
    try:
        year, month = (int(part) for part in period.split("-")[:2])
        return date(year, month, 1)
    except (ValueError, TypeError):
        return None


# proration -----------------------------------------------------------------


def billing_days_in_period(period: str) -> int:
    if not config.PRORATION_CALENDAR_MONTH:
        return config.BILLING_MONTH_DAYS
    start = period_start(period)
    if start is None:
        return config.BILLING_MONTH_DAYS
    from calendar import monthrange

    return monthrange(start.year, start.month)[1]


def daily_rate(monthly_fee: Decimal, period: str) -> Decimal:
    return Decimal(monthly_fee) / Decimal(billing_days_in_period(period))


def prorated_plan_charge(
    monthly_fee: Decimal, previous_monthly_fee: Decimal, change_day: int, period: str
) -> Decimal:
    if not change_day or int(change_day) <= 0:
        return _line(Decimal(monthly_fee))
    total_days = billing_days_in_period(period)
    days_on_old = max(0, min(int(change_day) - 1, total_days))
    days_on_new = total_days - days_on_old
    old_part = _line(daily_rate(Decimal(previous_monthly_fee), period) * days_on_old)
    new_part = _line(daily_rate(Decimal(monthly_fee), period) * days_on_new)
    return _line(old_part + new_part)


# rating --------------------------------------------------------------------


def usage_gb_rounded(usage_mb: int) -> int:
    usage_mb = int(usage_mb)
    gb, remainder = divmod(usage_mb, config.MB_PER_GB)
    return gb + (1 if remainder else 0)


def overage_gb(usage_mb: int, included_gb: int) -> int:
    return max(usage_gb_rounded(usage_mb) - int(included_gb), 0)


def overage_mb(usage_mb: int, included_gb: int) -> int:
    return max(int(usage_mb) - int(included_gb) * config.MB_PER_GB, 0)


def rate_overage(usage_mb: int, included_gb: int) -> Decimal:
    if config.RATING_EXACT_MB:
        return _line(Decimal(overage_mb(usage_mb, included_gb)) * config.OVERAGE_RATE_PER_MB)
    return _line(Decimal(overage_gb(usage_mb, included_gb)) * config.OVERAGE_RATE_PER_GB)


# promo ---------------------------------------------------------------------


def promo_is_live(issued_on: Optional[str], period: str) -> bool:
    issued = _parse(issued_on)
    cycle = period_start(period)
    if issued is None or cycle is None:
        return False
    if not config.PROMO_EXPIRY_ROLLING_DAYS:
        return (issued.year, issued.month) == (cycle.year, cycle.month)
    return issued + timedelta(days=config.PROMO_VALID_DAYS) >= cycle


def promo_credit(amount: Decimal, issued_on: Optional[str], period: str) -> Decimal:
    amount = Decimal(amount)
    if amount <= 0 or not promo_is_live(issued_on, period):
        return Decimal("0")
    return _line(amount)


# suspension ----------------------------------------------------------------


def suspended_days(start_day: int, end_day: int) -> int:
    start_day = int(start_day or 0)
    end_day = int(end_day or 0)
    if start_day <= 0 or end_day < start_day:
        return 0
    return end_day - start_day + 1


def suspension_credit(monthly_fee: Decimal, start_day: int, end_day: int, period: str) -> Decimal:
    if not config.SUSPENSION_CREDIT_DAILY_RATE:
        return Decimal("0")
    days = suspended_days(start_day, end_day)
    if not days:
        return Decimal("0")
    return _line(daily_rate(Decimal(monthly_fee), period) * days)


# multi line ----------------------------------------------------------------


def multi_line_pct(line_count: int) -> Decimal:
    for min_lines, pct in config.LINE_TIERS:
        if int(line_count) >= min_lines:
            return pct
    return Decimal("0")


def multi_line_discount(recurring_charge: Decimal, line_count: int) -> Decimal:
    return _line(Decimal(recurring_charge) * multi_line_pct(line_count) / Decimal(100))


# late fee ------------------------------------------------------------------


def days_past_due(due_date: Optional[str], period: str) -> int:
    due = _parse(due_date)
    cycle = period_start(period)
    if due is None or cycle is None:
        return 0
    return max((cycle - due).days, 0)


def late_fee(prior_balance: Decimal, due_date: Optional[str], period: str) -> Decimal:
    balance = Decimal(prior_balance)
    if balance <= 0 or days_past_due(due_date, period) <= config.LATE_FEE_GRACE_DAYS:
        return Decimal("0")
    return _line(balance * config.LATE_FEE_PCT / Decimal(100))


# tax -----------------------------------------------------------------------


def rates_for_province(province: str) -> TaxRates:
    return config.PROVINCE_RATES.get((province or "").upper(), config.DEFAULT_RATES)


def federal_tax(pre_discount_amount: Decimal, rates: TaxRates) -> Decimal:
    return _line(Decimal(pre_discount_amount) * rates.federal_pct / Decimal(100))


def provincial_tax(pre_discount_amount: Decimal, discount: Decimal, rates: TaxRates) -> Decimal:
    if rates.provincial_pct <= 0:
        return Decimal("0")
    base = Decimal(pre_discount_amount)
    if config.PROVINCIAL_TAX_POST_DISCOUNT:
        base -= Decimal(discount)
    if base < 0:
        base = Decimal("0")
    return _line(base * rates.provincial_pct / Decimal(100))


# loyalty -------------------------------------------------------------------


def loyalty_discount(amount: Decimal, loyalty_pct: float) -> Decimal:
    return _line(Decimal(amount) * Decimal(str(loyalty_pct)) / Decimal(100))


def apply_loyalty(amount: Decimal, loyalty_pct: float) -> Decimal:
    return _line(Decimal(amount) - loyalty_discount(amount, loyalty_pct))


# invoice orchestration -----------------------------------------------------


@dataclass
class InvoiceInputs:
    period: str
    province: str = ""
    usage_mb: int = 0
    included_gb: int = 0
    plan_fee: Decimal = field(default_factory=lambda: Decimal("0"))
    previous_plan_fee: Decimal = field(default_factory=lambda: Decimal("0"))
    plan_change_day: int = 0
    line_count: int = 1
    promo_amount: Decimal = field(default_factory=lambda: Decimal("0"))
    promo_issued_on: Optional[str] = None
    suspension_start_day: int = 0
    suspension_end_day: int = 0
    prior_balance: Decimal = field(default_factory=lambda: Decimal("0"))
    prior_due_date: Optional[str] = None
    loyalty_pct: float = 0.0


@dataclass
class InvoiceAmounts:
    usage_gb_rated: int
    overage_gb: int
    overage_mb: int
    plan_charge: Decimal
    line_discount: Decimal
    recurring: Decimal
    overage_charges: Decimal
    suspension_credit: Decimal
    promo_credit: Decimal
    late_fee: Decimal
    subtotal: Decimal
    loyalty_discount: Decimal
    federal_tax: Decimal
    provincial_tax: Decimal
    federal_label: str
    provincial_label: str
    total: Decimal


def compute_invoice_amounts(inputs: InvoiceInputs) -> InvoiceAmounts:
    """The one invoice formula.

    recurring = plan_charge - line_discount
    subtotal  = max(recurring + overage + late_fee - suspension - promo, 0)
    total     = subtotal - loyalty + federal_tax + provincial_tax
    """
    plan_charge = prorated_plan_charge(
        inputs.plan_fee, inputs.previous_plan_fee, inputs.plan_change_day, inputs.period
    )
    line_discount = multi_line_discount(plan_charge, inputs.line_count)
    recurring = _line(plan_charge - line_discount)
    overage_charges = rate_overage(inputs.usage_mb, inputs.included_gb)
    credit = suspension_credit(
        inputs.plan_fee, inputs.suspension_start_day, inputs.suspension_end_day, inputs.period
    )
    promo = promo_credit(inputs.promo_amount, inputs.promo_issued_on, inputs.period)
    fee = late_fee(inputs.prior_balance, inputs.prior_due_date, inputs.period)

    subtotal = _line(max(recurring + overage_charges + fee - credit - promo, Decimal("0")))

    rates = rates_for_province(inputs.province)
    loyalty = loyalty_discount(subtotal, inputs.loyalty_pct)
    federal = federal_tax(subtotal, rates)
    provincial = provincial_tax(subtotal, loyalty, rates)

    return InvoiceAmounts(
        usage_gb_rated=usage_gb_rounded(inputs.usage_mb),
        overage_gb=overage_gb(inputs.usage_mb, inputs.included_gb),
        overage_mb=overage_mb(inputs.usage_mb, inputs.included_gb),
        plan_charge=plan_charge,
        line_discount=line_discount,
        recurring=recurring,
        overage_charges=overage_charges,
        suspension_credit=credit,
        promo_credit=promo,
        late_fee=fee,
        subtotal=subtotal,
        loyalty_discount=loyalty,
        federal_tax=federal,
        provincial_tax=provincial,
        federal_label=rates.federal_label,
        provincial_label=rates.provincial_label,
        total=money(subtotal - loyalty + federal + provincial),
    )
