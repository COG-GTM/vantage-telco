import json
from json import dumps
from pathlib import Path
from unittest.mock import MagicMock

import mongomock
import pytest
from fastapi.testclient import TestClient

from app import db
from app.billing.invoices import (
    account_index,
    accounts,
    find_account,
    unlinked_usage,
)
from app.inventory.repository import enrich_site, list_sites
from app.main import app
from app.security import SCOPE_BILLING_OPS


@pytest.fixture(autouse=True)
def reset_client(monkeypatch: pytest.MonkeyPatch):
    db.close_client()
    monkeypatch.delenv("MONGO_URI", raising=False)
    yield
    db.close_client()
    monkeypatch.delenv("MONGO_URI", raising=False)


def test_single_client_reuse(monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setenv("MONGO_URI", "mongodb://example/")
    fake = MagicMock()
    monkeypatch.setattr("pymongo.MongoClient", fake)

    db.get_collection("usage")
    db.get_collection("usage")
    db.get_collection("usage")
    db.get_collection("accounts")

    fake.assert_called_once_with("mongodb://example/")
    db.close_client()
    fake.return_value.close.assert_called_once()
    assert db._client is None


def test_seed_fallback_when_unset():
    assert isinstance(db.get_collection("usage"), db.SeedCollection)
    with pytest.raises(KeyError):
        db.get_collection("nope")


def test_find_documents_matcher_semantics():
    collection = db.SeedCollection([{"a": 1}, {"a": None}, {"a": ""}, {"b": 2}])

    assert len(list(collection.find({"a": 1}))) == 1
    assert len(list(collection.find({"a": {"$in": [None, ""]}}))) == 3
    assert len(list(collection.find({}))) == 4
    assert len(list(collection.find({"a": None}))) == 2


def test_unlinked_usage_matches_python_filter():
    usage = db.all_documents("usage")
    expected_period = [r for r in usage if not r.get("account_id") and r.get("period") == "2026-07"]
    expected_all = [r for r in usage if not r.get("account_id")]

    assert unlinked_usage("2026-07") == expected_period
    assert unlinked_usage() == expected_all
    assert len(unlinked_usage()) == 2


def test_list_sites_pushdown_matches_python_filter():
    sites = db.all_documents("sites")
    market_id = sites[0]["market_id"]
    expected = [
        enrich_site(site)
        for site in sites
        if site["market_id"] == market_id and site["lifecycle_state"] == "ACTIVE"
    ]

    assert list_sites(market_id, "ACTIVE") == expected


def test_ensure_indexes_with_mongomock(monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setenv("MONGO_URI", "mongodb://example/")
    monkeypatch.setattr("pymongo.MongoClient", mongomock.MongoClient)

    db.ensure_indexes()

    for name, fields in db.REQUIRED_INDEXES.items():
        indexes = db.get_collection(name).index_information().values()
        for field in fields:
            assert any(index["key"] == [(field, 1)] for index in indexes)


def test_ensure_indexes_noop_in_seed_mode():
    db.ensure_indexes()
    assert db._client is None


def test_find_documents_mongo_mode_uses_find(monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setenv("MONGO_URI", "mongodb://example/")
    monkeypatch.setattr("pymongo.MongoClient", mongomock.MongoClient)
    collection = db.get_collection("usage")
    collection.insert_many(
        [
            {"account_id": "A", "period": "2026-07"},
            {"account_id": None, "period": "2026-07"},
        ]
    )

    result = unlinked_usage("2026-07")

    assert len(result) == 1
    assert {key: result[0][key] for key in ("account_id", "period")} == {
        "account_id": None,
        "period": "2026-07",
    }


def test_lifespan_closes_client(monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setenv("MONGO_URI", "mongodb://example/")
    monkeypatch.setattr("pymongo.MongoClient", mongomock.MongoClient)

    with TestClient(app):
        assert db._client is not None
    assert db._client is None


def test_billing_invoices_match_phase0_baseline(token_for):
    baseline_path = Path("docs/modernization/phase0-baseline/pre-billing-invoices.json")
    with baseline_path.open() as handle:
        baseline = json.load(handle)

    token = token_for([SCOPE_BILLING_OPS])
    with TestClient(app, headers={"Authorization": f"Bearer {token}"}) as client:
        result = client.get("/billing/invoices?period=2026-07").json()

    assert dumps(result, sort_keys=True) == dumps(baseline, sort_keys=True)


def test_account_index_matches_find_account():
    indexed = account_index()
    assert all(
        indexed[account["account_id"]] == find_account(account["account_id"])
        for account in accounts()
    )
