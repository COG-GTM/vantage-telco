"""Multi-line discount off the recurring charge, from telco-rules.

Three to nine lines discount 5%, ten or more discount 10%.
"""

from __future__ import annotations

from decimal import Decimal

import telco_rules


def multi_line_pct(line_count: int) -> Decimal:
    return Decimal(str(telco_rules.multi_line_pct(int(line_count))))


def multi_line_discount(recurring_charge: Decimal, line_count: int) -> Decimal:
    return Decimal(str(telco_rules.multi_line_discount(float(recurring_charge), int(line_count))))
