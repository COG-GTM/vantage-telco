"""Cross-estate invoice parity.

Rates the same customer book under two estate policies, joins on
``billing_ref`` and prints every account whose total disagrees, with the rules
implicated and the variance by rule and by province.

    python tools/parity.py --period 2026-07 --left meridian --right vantage

Exit status is 0 when every account agrees, 1 otherwise.
"""

from __future__ import annotations

import argparse
import sys
from decimal import Decimal
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from oss.model import Invoice  # noqa: E402
from oss.service import get_estate  # noqa: E402

CENT = Decimal("0.01")

RULE_FIELDS = (
    ("overage_charges", "rating"),
    ("plan_charge", "proration"),
    ("promo_credit", "promo-expiry"),
    ("suspension_credit", "suspension"),
    ("provincial_tax", "tax-base"),
    ("late_fee", "late-fee"),
    ("line_discount", "multi-line"),
    ("loyalty_discount", "loyalty"),
)


def by_ref(invoices: list[Invoice]) -> dict[str, Invoice]:
    return {i.billing_ref: i for i in invoices}


def implicated_rules(left: Invoice, right: Invoice) -> list[str]:
    hints = []
    plan_agrees = abs(left.plan_charge - right.plan_charge) <= CENT
    for field, label in RULE_FIELDS:
        delta = abs(rule_amount(left, field) - rule_amount(right, field))
        if delta <= CENT:
            continue
        # A line discount only diverges on its own if the charge it comes off agreed.
        if label in {"multi-line", "loyalty"} and not plan_agrees:
            continue
        hints.append(label)
    if not hints:
        hints.append("rounding")
    return hints


def rule_amount(invoice: Invoice, field: str) -> Decimal:
    values: dict[str, Decimal] = {
        "overage_charges": invoice.overage_charges,
        "plan_charge": invoice.plan_charge,
        "promo_credit": invoice.promo_credit,
        "suspension_credit": invoice.suspension_credit,
        "provincial_tax": invoice.provincial_tax,
        "late_fee": invoice.late_fee,
        "line_discount": invoice.line_discount,
        "loyalty_discount": invoice.loyalty_discount,
    }
    return values[field]


def compare(period: str, left_name: str, right_name: str) -> dict[str, Any]:
    left = by_ref(get_estate(left_name).invoices(period=period))
    right = by_ref(get_estate(right_name).invoices(period=period))
    shared = sorted(set(left) & set(right))

    rows = []
    by_rule: dict[str, Decimal] = {}
    by_province: dict[str, Decimal] = {}
    for ref in shared:
        delta = right[ref].total - left[ref].total
        if abs(delta) <= CENT:
            continue
        rules = implicated_rules(left[ref], right[ref])
        rows.append(
            {
                "billing_ref": ref,
                "province": left[ref].province,
                f"{left_name}_total": left[ref].total,
                f"{right_name}_total": right[ref].total,
                "delta": delta,
                "rules": rules,
            }
        )
        for rule in rules:
            by_rule[rule] = by_rule.get(rule, Decimal("0")) + delta
        province = left[ref].province
        by_province[province] = by_province.get(province, Decimal("0")) + delta

    return {
        "period": period,
        "left": left_name,
        "right": right_name,
        "accounts_compared": len(shared),
        "left_only": sorted(set(left) - set(right)),
        "right_only": sorted(set(right) - set(left)),
        "differences": rows,
        "variance_by_rule": by_rule,
        "variance_by_province": by_province,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--period", default="2026-07")
    parser.add_argument("--left", default="meridian")
    parser.add_argument("--right", default="vantage")
    parser.add_argument("--limit", type=int, default=20)
    args = parser.parse_args()

    report = compare(args.period, args.left, args.right)
    print(f"period {report['period']}  {args.left} vs {args.right}")
    print(f"accounts compared: {report['accounts_compared']}")
    print(f"disagreeing accounts: {len(report['differences'])}\n")

    if report["differences"]:
        print(f"{'BILLING_REF':<14}{'PRV':<5}{args.left:>14}{args.right:>14}{'DELTA':>12}  RULES")
        for row in report["differences"][: args.limit]:
            print(
                f"{row['billing_ref']:<14}{row['province']:<5}"
                f"{row[args.left + '_total']:>14.2f}{row[args.right + '_total']:>14.2f}"
                f"{row['delta']:>12.2f}  {','.join(row['rules'])}"
            )
        remaining = len(report["differences"]) - args.limit
        if remaining > 0:
            print(f"... {remaining} more")

        print("\nvariance by rule")
        for rule, amount in sorted(report["variance_by_rule"].items(), key=lambda kv: -abs(kv[1])):
            print(f"  {rule:<14}{amount:>14.2f}")
        print("\nvariance by province")
        for province, amount in sorted(report["variance_by_province"].items()):
            print(f"  {province:<14}{amount:>14.2f}")

    return 1 if report["differences"] else 0


if __name__ == "__main__":
    raise SystemExit(main())
