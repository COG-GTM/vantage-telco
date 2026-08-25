"""The merged engine under the Vantage policy reproduces the FastAPI service.

``tests/golden/vantage-*.json`` is ``app.billing.invoices.list_invoices()`` from
vantage-telco, captured unchanged.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from oss.service import get_estate

GOLDEN = Path(__file__).parent / "golden"
PERIODS = ("2026-06", "2026-07")

FIELDS = (
    "plan_charge",
    "line_discount",
    "recurring",
    "overage_charges",
    "suspension_credit",
    "promo_credit",
    "late_fee",
    "subtotal",
    "loyalty_discount",
    "federal_tax",
    "provincial_tax",
)


def service_invoices(period: str) -> dict[str, dict[str, float]]:
    records = json.loads((GOLDEN / f"vantage-{period}.json").read_text())
    return {r["billing_ref"]: r for r in records}


@pytest.mark.parametrize("period", PERIODS)
def test_every_account_matches_the_service(period: str) -> None:
    expected = service_invoices(period)
    merged = {i.billing_ref: i for i in get_estate("vantage").invoices(period=period)}

    assert set(merged) == set(expected)
    for ref, invoice in merged.items():
        record = expected[ref]
        for field in FIELDS:
            assert float(getattr(invoice, field)) == pytest.approx(
                record[field], abs=0.005
            ), f"{ref} {field}"
        assert float(invoice.total) == pytest.approx(record["invoice_total"], abs=0.005)
        assert invoice.overage_mb == record["overage_mb"]


@pytest.mark.parametrize("period", PERIODS)
def test_unlinked_usage_is_never_invoiced(period: str) -> None:
    estate = get_estate("vantage")
    invoiced = {i.account_id for i in estate.invoices(period=period)}
    for usage in estate.unlinked_usage(period=period):
        assert usage.account_id not in invoiced
