"""The parity report: what it joins on and what it attributes."""

from __future__ import annotations

from decimal import Decimal

import pytest

from oss.service import get_estate
from tools.parity import compare, implicated_rules

PERIOD = "2026-07"


@pytest.fixture(scope="module")
def report():
    return compare(PERIOD, "meridian", "vantage")


def test_the_two_books_join_on_billing_ref(report) -> None:
    assert report["accounts_compared"] > 0
    assert report["left_only"] == []
    assert report["right_only"] == []


def test_the_estates_really_do_disagree_on_this_book(report) -> None:
    assert report["differences"], "the merge would be pointless if the rules agreed"
    assert len(report["differences"]) <= report["accounts_compared"]


def test_every_difference_names_the_rules_behind_it(report) -> None:
    for row in report["differences"]:
        assert row["rules"]
        assert row["delta"] == row["vantage_total"] - row["meridian_total"]


def test_variance_adds_up_to_the_difference_between_the_registers(report) -> None:
    total = sum(row["delta"] for row in report["differences"])
    assert sum(report["variance_by_province"].values()) == total


def test_an_account_rated_against_itself_shows_no_variance() -> None:
    same = compare(PERIOD, "vantage", "vantage")
    assert same["differences"] == []


def test_a_pure_rounding_difference_is_labelled_as_such() -> None:
    invoice = get_estate("meridian").invoices(period=PERIOD)[0]
    nudged = type(invoice)(**{**invoice.__dict__, "total": invoice.total + Decimal("0.02")})
    assert implicated_rules(invoice, nudged) == ["rounding"]
