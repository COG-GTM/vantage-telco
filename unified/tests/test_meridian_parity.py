"""The merged engine under the Meridian policy reproduces the legacy register.

``tests/golden/meridian-*.jsonl`` is the output of the C++ ``bin/billing-run
--period <p> --json`` in meridian-telco, captured unchanged. Every charge line
on every account has to match to the cent, otherwise the merge changed a bill.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from oss.service import get_estate

GOLDEN = Path(__file__).parent / "golden"
PERIODS = ("2026-06", "2026-07")

FIELDS = (
    ("plan_charge", "plan_charge"),
    ("line_discount", "line_discount"),
    ("overage_charges", "overage_charges"),
    ("suspension_credit", "suspension_credit"),
    ("promo_credit", "promo_credit"),
    ("late_fee", "late_fee"),
    ("subtotal", "subtotal"),
    ("loyalty", "loyalty_discount"),
    ("federal_tax", "federal_tax"),
    ("provincial_tax", "provincial_tax"),
    ("total", "total"),
)


def legacy_register(period: str) -> dict[str, dict[str, float]]:
    records: list[dict[str, float]] = [
        json.loads(line)
        for line in (GOLDEN / f"meridian-{period}.jsonl").read_text().splitlines()
        if line.strip()
    ]
    return {r["billing_ref"]: r for r in records}


@pytest.mark.parametrize("period", PERIODS)
def test_every_account_matches_the_legacy_register(period: str) -> None:
    legacy = legacy_register(period)
    merged = {i.billing_ref: i for i in get_estate("meridian").invoices(period=period)}

    assert set(merged) == set(legacy)
    for ref, invoice in merged.items():
        record = legacy[ref]
        for legacy_field, merged_field in FIELDS:
            assert float(getattr(invoice, merged_field)) == pytest.approx(
                record[legacy_field], abs=0.005
            ), f"{ref} {legacy_field}"
        assert invoice.overage_gb == record["overage_gb"]
        assert invoice.usage_mb == record["usage_mb"]


@pytest.mark.parametrize("period", PERIODS)
def test_register_revenue_matches(period: str) -> None:
    legacy_total = sum(r["total"] for r in legacy_register(period).values())
    assert float(get_estate("meridian").revenue_total(period=period)) == pytest.approx(
        legacy_total, abs=0.01
    )
