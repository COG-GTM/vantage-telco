"""Suspension inside a cycle, from telco-rules (DECISIONS.md D-04).

A suspended line stays provisioned and is billed in full: there is no credit.
"""

from __future__ import annotations

from decimal import Decimal
from typing import Optional

import telco_rules


def suspended_days(start_day: int, end_day: int) -> int:
    return telco_rules.suspended_days(int(start_day or 0), int(end_day or 0))


def suspension_credit(monthly_fee: Decimal, start_day: int, end_day: int, period: Optional[str] = None) -> Decimal:
    return Decimal(str(telco_rules.suspension_credit(float(monthly_fee), int(start_day or 0), int(end_day or 0))))
