"""Promotional credits, from telco-rules (DECISIONS.md D-02).

A promo credit is live only in the billing cycle it was issued in.
"""

from __future__ import annotations

from decimal import Decimal
from typing import Optional

import telco_rules


def promo_is_live(issued_on: Optional[str], period: str) -> bool:
    return telco_rules.promo_is_live(issued_on or "", period)


def promo_credit(amount: Decimal, issued_on: Optional[str], period: str) -> Decimal:
    return Decimal(str(telco_rules.promo_credit(float(amount), issued_on or "", period)))
