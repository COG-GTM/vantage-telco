"""The HTTP surface, which serves either estate from one code path."""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from oss.api.main import app

client = TestClient(app)


def test_the_estates_endpoint_publishes_the_rules_each_one_runs() -> None:
    payload = client.get("/estates").json()
    names = {e["estate"] for e in payload}
    assert {"meridian", "vantage", "vantage-report"} <= names
    meridian = next(e for e in payload if e["estate"] == "meridian")
    assert meridian["billing_rules"]["rating_basis"] == "whole_gb"
    assert meridian["inventory_rules"]["active_circuit_roles"] == "all"


@pytest.mark.parametrize("estate", ["meridian", "vantage"])
def test_invoices_are_served_per_estate(estate: str) -> None:
    response = client.get("/billing/invoices", params={"estate": estate, "period": "2026-07"})
    assert response.status_code == 200
    invoices = response.json()
    assert invoices
    assert {i["estate"] for i in invoices} == {estate}


def test_the_same_account_bills_differently_on_each_estate() -> None:
    def total(estate: str) -> float:
        rows = client.get(
            "/billing/invoices", params={"estate": estate, "period": "2026-07"}
        ).json()
        return sum(r["total"] for r in rows)

    assert total("meridian") != total("vantage")


def test_an_unknown_estate_is_rejected() -> None:
    assert client.get("/billing/invoices", params={"estate": "nope"}).status_code == 404


def test_capacity_answers_a_bandwidth_request() -> None:
    rows = client.get("/capacity", params={"estate": "vantage", "requested_mbps": 100}).json()
    assert rows
    assert all("can_support" in row for row in rows)


def test_parity_is_served_over_http() -> None:
    report = client.get("/parity", params={"period": "2026-07"}).json()
    assert report["left"] == "meridian"
    assert report["right"] == "vantage"
    assert report["accounts_compared"] > 0
