"""Arithmetic and rounding.

Two differences live here. Meridian rounds every charge line to cents as it is
produced and the total is the sum of rounded lines; Vantage carries full
precision and rounds once, at the total. And Meridian's register is a C++
double register, so a rate applied to a charge lands on the binary value the
legacy run produced (a half cent can fall the other way), while Vantage works
in decimal throughout. Reproducing a legacy invoice to the cent needs both.
"""

from __future__ import annotations

import math
from decimal import ROUND_HALF_UP, Decimal

from oss.policy import Arithmetic, BillingPolicy, Rounding

CENT = Decimal("0.01")


def money(amount: Decimal) -> Decimal:
    return Decimal(amount).quantize(CENT, rounding=ROUND_HALF_UP)


def binary_money(amount: Decimal) -> Decimal:
    """``floor(amount * 100 + 0.5) / 100`` evaluated in doubles.

    The legacy register rounds this way, and on a half cent the double product
    decides which side it falls on. Rounding the decimal value instead moves a
    handful of invoices by a cent.
    """
    return Decimal(math.floor(float(amount) * 100.0 + 0.5)) / Decimal(100)


def line(amount: Decimal, policy: BillingPolicy) -> Decimal:
    """Round a charge line if the estate rounds line by line."""
    if policy.rounding is not Rounding.PER_LINE:
        return Decimal(amount)
    if policy.arithmetic is Arithmetic.BINARY64:
        return binary_money(amount)
    return money(amount)


def pct_of(amount: Decimal, pct: Decimal, policy: BillingPolicy) -> Decimal:
    """``amount * pct / 100`` in the estate's arithmetic."""
    if policy.arithmetic is Arithmetic.BINARY64:
        return Decimal(float(amount) * float(pct) / 100.0)
    return Decimal(amount) * Decimal(pct) / Decimal(100)


def divide(amount: Decimal, divisor: int, policy: BillingPolicy) -> Decimal:
    if policy.arithmetic is Arithmetic.BINARY64:
        return Decimal(float(amount) / float(divisor))
    return Decimal(amount) / Decimal(divisor)


def multiply(amount: Decimal, factor: int, policy: BillingPolicy) -> Decimal:
    if policy.arithmetic is Arithmetic.BINARY64:
        return Decimal(float(amount) * float(factor))
    return Decimal(amount) * Decimal(factor)
