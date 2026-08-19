"""The vendored rules library must still be the library, unmodified, and must
still reproduce the shared conformance vectors.
"""

from decimal import Decimal
from pathlib import Path
import subprocess
import sys

import pytest

from app.billing.rules import InvoiceInputs, compute_invoice_amounts

VENDOR = Path(__file__).resolve().parents[1] / "vendor"
VECTORS = VENDOR / "conformance" / "vectors.tsv"

CHECKED = [
    "overage_charges",
    "plan_charge",
    "line_discount",
    "suspension_credit",
    "promo_credit",
    "late_fee",
    "subtotal",
    "loyalty_discount",
    "federal_tax",
    "provincial_tax",
    "total",
]


def _vectors():
    rows = []
    lines = [l for l in VECTORS.read_text().splitlines() if l.strip() and not l.startswith("#")]
    header = lines[0].split("|")
    for line in lines[1:]:
        rows.append(dict(zip(header, line.split("|"))))
    return rows


def test_vendored_library_is_unmodified():
    result = subprocess.run(
        [sys.executable, str(VENDOR / "vendor_check.py")], capture_output=True, text=True
    )
    assert result.returncode == 0, result.stdout + result.stderr


@pytest.mark.parametrize("row", _vectors(), ids=lambda r: r["name"])
def test_conformance_vector(row):
    amounts = compute_invoice_amounts(
        InvoiceInputs(
            period=row["period"],
            province=row["province"],
            usage_mb=int(row["usage_mb"]),
            included_gb=int(row["included_gb"]),
            plan_fee=Decimal(row["plan_fee"]),
            previous_plan_fee=Decimal(row["previous_plan_fee"]),
            plan_change_day=int(row["plan_change_day"]),
            line_count=int(row["line_count"]),
            promo_amount=Decimal(row["promo_amount"]),
            promo_issued_on=row["promo_issued_on"] or None,
            suspension_start_day=int(row["suspension_start_day"]),
            suspension_end_day=int(row["suspension_end_day"]),
            prior_balance=Decimal(row["prior_balance"]),
            prior_due_date=row["prior_due_date"] or None,
            loyalty_pct=float(row["loyalty_pct"]),
        )
    )
    assert amounts.overage_gb == int(row["overage_gb"])
    for name in CHECKED:
        assert getattr(amounts, name) == Decimal(row[name]), name
