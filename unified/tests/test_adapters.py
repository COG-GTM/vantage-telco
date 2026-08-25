"""The adapters, which normalise two incompatible source formats.

Meridian keeps flat ``.rec`` account files and CSV exports; Vantage keeps JSON
collections. Everything above the adapters sees the same model.
"""

from __future__ import annotations

from decimal import Decimal
from pathlib import Path

import pytest

from oss.model import Account, Device, UsageRecord
from oss.service import get_estate

DATA = Path(__file__).resolve().parents[1] / "data"


@pytest.mark.parametrize("estate_name", ["meridian", "vantage"])
def test_both_books_normalise_to_the_same_model(estate_name: str) -> None:
    estate = get_estate(estate_name)
    assert all(isinstance(a, Account) for a in estate.accounts())
    assert all(isinstance(u, UsageRecord) for u in estate.usage())
    assert all(isinstance(d, Device) for d in estate.devices())


def test_every_meridian_account_record_is_read() -> None:
    on_disk = len(list((DATA / "meridian" / "accounts").glob("*.rec")))
    assert on_disk > 0
    assert len(get_estate("meridian").accounts()) == on_disk


def test_money_from_both_sources_arrives_as_decimal() -> None:
    for name in ("meridian", "vantage"):
        account = get_estate(name).accounts()[0]
        assert isinstance(account.plan_monthly_fee, Decimal)
        assert isinstance(account.prior_balance, Decimal)


def test_the_two_books_describe_the_same_customers() -> None:
    meridian = {a.billing_ref for a in get_estate("meridian").accounts()}
    vantage = {a.billing_ref for a in get_estate("vantage").accounts()}
    assert meridian == vantage


def test_usage_with_no_account_is_carried_but_not_invoiced() -> None:
    estate = get_estate("vantage")
    unlinked = estate.unlinked_usage()
    invoiced = {i.account_id for i in estate.invoices()}
    assert all(u.account_id not in invoiced for u in unlinked)
