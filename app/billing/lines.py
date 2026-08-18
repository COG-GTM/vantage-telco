"""Multi-line discount off the recurring charge.

Three to nine lines discount 5%, ten or more discount 10%. Same schedule as the
published rate card.
"""

from __future__ import annotations

from decimal import Decimal


def multi_line_pct(line_count: int) -> Decimal:
    if line_count >= 10:
        return Decimal("10")
    if line_count >= 3:
        return Decimal("5")
    return Decimal("0")


def multi_line_discount(recurring_charge: Decimal, line_count: int) -> Decimal:
    return Decimal(recurring_charge) * multi_line_pct(int(line_count)) / Decimal(100)
