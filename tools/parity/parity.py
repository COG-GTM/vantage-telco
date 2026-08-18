"""Cross-engine invoice parity.

Runs the meridian-telco billing register and the vantage-telco billing service
over the same accounts and the same usage feed, joins the two on ``billing_ref``
and prints every account where the invoice totals disagree.

    python tools/parity/parity.py --period 2026-07 [--meridian-dir ../meridian-telco]

Expected clone layout (override with --meridian-dir or MERIDIAN_DIR):

    <workspace>/vantage-telco
    <workspace>/meridian-telco

The meridian binaries are built on demand with ``make -C <meridian-dir>``.
Exit status is 0 when every account agrees, 1 otherwise.
"""

from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
from decimal import Decimal
from pathlib import Path
from typing import Any, Dict, List

REPO_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO_ROOT))

from app.billing import invoices as vantage_invoices  # noqa: E402

CENT = Decimal("0.01")


def meridian_invoices(meridian_dir: Path, period: str, build: bool = True) -> Dict[str, Dict[str, Any]]:
    binary = meridian_dir / "bin" / "billing-run"
    if build:
        subprocess.run(["make", "-s", "-C", str(meridian_dir)], check=True)
    if not binary.exists():
        raise SystemExit(f"{binary} not found; build meridian-telco first")
    result = subprocess.run(
        [str(binary), "--period", period, "--json"],
        cwd=str(meridian_dir),
        check=True,
        capture_output=True,
        text=True,
    )
    out = {}
    for line in result.stdout.splitlines():
        line = line.strip()
        if not line:
            continue
        record = json.loads(line)
        out[record["billing_ref"]] = record
    return out


def vantage_invoices_by_ref(period: str) -> Dict[str, Dict[str, Any]]:
    return {i["billing_ref"]: i for i in vantage_invoices.list_invoices(period=period)}


def _rule_hints(legacy: Dict[str, Any], modern: Dict[str, Any]) -> List[str]:
    hints = []
    if abs(Decimal(str(legacy["overage_charges"])) - Decimal(str(modern["overage_charges"]))) > CENT:
        hints.append("overage")
    plan_charges_agree = abs(Decimal(str(legacy["plan_charge"])) - Decimal(str(modern["plan_charge"]))) <= CENT
    if not plan_charges_agree:
        hints.append("proration")
    if abs(Decimal(str(legacy["promo_credit"])) - Decimal(str(modern["promo_credit"]))) > CENT:
        hints.append("promo-expiry")
    if abs(Decimal(str(legacy["suspension_credit"])) - Decimal(str(modern["suspension_credit"]))) > CENT:
        hints.append("suspension")
    if abs(Decimal(str(legacy["provincial_tax"])) - Decimal(str(modern["provincial_tax"]))) > CENT:
        hints.append("tax-base")
    if abs(Decimal(str(legacy["late_fee"])) - Decimal(str(modern["late_fee"]))) > CENT:
        hints.append("late-fee")
    # Only a real multi-line divergence if the charge it is taken from agreed.
    if plan_charges_agree and abs(Decimal(str(legacy["line_discount"])) - Decimal(str(modern["line_discount"]))) > CENT:
        hints.append("multi-line")
    if not hints:
        hints.append("rounding")
    return hints


def compare(period: str, meridian_dir: Path, build: bool = True, limit: int = 25) -> int:
    legacy = meridian_invoices(meridian_dir, period, build=build)
    modern = vantage_invoices_by_ref(period)
    refs = sorted(set(legacy) & set(modern))
    missing = sorted(set(legacy) ^ set(modern))

    rows = []
    variance = Decimal("0")
    by_rule: Dict[str, Decimal] = {}
    by_province: Dict[str, Decimal] = {}

    for ref in refs:
        left = legacy[ref]
        right = modern[ref]
        delta = Decimal(str(right["invoice_total"])) - Decimal(str(left["total"]))
        if abs(delta) <= Decimal("0"):
            continue
        hints = _rule_hints(left, right)
        variance += abs(delta)
        for hint in hints:
            by_rule[hint] = by_rule.get(hint, Decimal("0")) + abs(delta)
        province = left["province"]
        by_province[province] = by_province.get(province, Decimal("0")) + abs(delta)
        rows.append((ref, left["cust_nm"][:26], province, left["total"], right["invoice_total"], delta, ",".join(hints)))

    print(f"invoice parity  period={period}  accounts={len(refs)}  differing={len(rows)}")
    if missing:
        print(f"accounts present in only one system: {', '.join(missing[:10])}")
    print()
    print(f"{'REF':<9} {'CUSTOMER':<26} {'PRV':<4} {'MERIDIAN':>12} {'VANTAGE':>12} {'DELTA':>11}  RULES")
    print("-" * 104)
    for row in rows[:limit]:
        ref, name, province, left_total, right_total, delta, hints = row
        print(f"{ref:<9} {name:<26} {province:<4} {left_total:>12.2f} {right_total:>12.2f} {delta:>11.2f}  {hints}")
    if len(rows) > limit:
        print(f"... {len(rows) - limit} more differing accounts")
    print("-" * 104)
    print(f"absolute variance: ${variance:,.2f} across {len(rows)} accounts")
    if by_rule:
        print("by rule:      " + "  ".join(f"{rule}=${amount:,.2f}" for rule, amount in sorted(by_rule.items())))
    if by_province:
        print("by province:  " + "  ".join(f"{prov}=${amount:,.2f}" for prov, amount in sorted(by_province.items())))

    if rows:
        print("\nPARITY FAILED")
        return 1
    print("\nPARITY OK")
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--period", default="2026-07")
    parser.add_argument(
        "--meridian-dir",
        default=os.environ.get("MERIDIAN_DIR", str(REPO_ROOT.parent / "meridian-telco")),
    )
    parser.add_argument("--no-build", action="store_true", help="use the meridian binaries as they are")
    parser.add_argument("--limit", type=int, default=25)
    args = parser.parse_args()

    meridian_dir = Path(args.meridian_dir).resolve()
    if not (meridian_dir / "billing").is_dir():
        raise SystemExit(
            f"no meridian-telco checkout at {meridian_dir}\n"
            "clone it beside this repo or pass --meridian-dir / MERIDIAN_DIR"
        )
    return compare(args.period, meridian_dir, build=not args.no_build, limit=args.limit)


if __name__ == "__main__":
    raise SystemExit(main())
