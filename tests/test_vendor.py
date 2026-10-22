"""The vendored telco-billing-rules copy is untouched and passes its own conformance vectors."""

import subprocess
import sys
from decimal import Decimal
from pathlib import Path

import pytest

import app.billing  # noqa: F401
from billing_rules import InvoiceInputs, compute_invoice_amounts

VENDOR = Path(__file__).resolve().parents[1] / "vendor"


def test_vendored_copy_is_not_patched_in_place():
    result = subprocess.run([sys.executable, str(VENDOR / "vendor_check.py")], capture_output=True, text=True)
    assert result.returncode == 0, result.stdout


def _vectors():
    lines = [l for l in (VENDOR / "conformance" / "vectors.tsv").read_text().splitlines() if l.strip() and not l.startswith("#")]
    header = lines[0].split("|")
    return [dict(zip(header, line.split("|"))) for line in lines[1:]]


@pytest.mark.parametrize("row", _vectors(), ids=lambda row: row["name"])
def test_vendored_binding_matches_conformance_vectors(row):
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
    for field in ("plan_charge", "line_discount", "overage_charges", "suspension_credit", "promo_credit",
                  "late_fee", "subtotal", "loyalty_discount", "federal_tax", "provincial_tax", "total"):
        assert getattr(amounts, field) == Decimal(row[field]), field
