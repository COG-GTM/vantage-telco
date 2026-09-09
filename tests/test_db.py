from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import pytest
from fastapi.testclient import TestClient

from app import db
from app.billing import invoices as invoice_service
from app.inventory import repository
from app.main import app

FIXTURE = Path(__file__).parent / "fixtures" / "invoices_2026-07.json"


class FakeCollection:
    def __init__(self) -> None:
        self.indexes: list[str] = []

    def create_index(self, field: str) -> str:
        self.indexes.append(field)
        return f"{field}_1"

    def find(self, query: dict[str, Any]) -> list[dict[str, Any]]:
        return [{"query": query}]


class FakeDatabase:
    def __init__(self) -> None:
        self.collections: dict[str, FakeCollection] = {}

    def __getitem__(self, name: str) -> FakeCollection:
        return self.collections.setdefault(name, FakeCollection())


class FakeMongoClient:
    instances: list[FakeMongoClient] = []

    def __init__(self, uri: str) -> None:
        self.uri = uri
        self.closed = False
        self.databases: dict[str, FakeDatabase] = {}
        FakeMongoClient.instances.append(self)

    def __getitem__(self, name: str) -> FakeDatabase:
        return self.databases.setdefault(name, FakeDatabase())

    def close(self) -> None:
        self.closed = True


@pytest.fixture
def mongo_mode(monkeypatch):
    import pymongo

    FakeMongoClient.instances = []
    monkeypatch.setattr(pymongo, "MongoClient", FakeMongoClient)
    monkeypatch.setenv("MONGO_URI", "mongodb://fake:27017")
    monkeypatch.delenv("MONGO_DB", raising=False)
    db.close_client()
    yield FakeMongoClient
    db.close_client()


def test_single_client_reused_across_many_get_collection_calls(mongo_mode):
    for _ in range(50):
        for name in db.COLLECTIONS:
            db.get_collection(name)
    assert len(mongo_mode.instances) == 1
    assert mongo_mode.instances[0].uri == "mongodb://fake:27017"


def test_close_client_then_reopen_builds_new_client(mongo_mode):
    db.get_collection("sites")
    db.close_client()
    assert mongo_mode.instances[0].closed is True
    db.get_collection("sites")
    assert len(mongo_mode.instances) == 2


def test_uri_change_replaces_client(mongo_mode, monkeypatch):
    db.get_collection("sites")
    monkeypatch.setenv("MONGO_URI", "mongodb://other:27017")
    db.get_collection("sites")
    assert len(mongo_mode.instances) == 2
    assert mongo_mode.instances[0].closed is True


def test_get_collection_uses_mongo_db_env(mongo_mode, monkeypatch):
    monkeypatch.setenv("MONGO_DB", "custom")
    db.get_collection("usage")
    assert list(mongo_mode.instances[0].databases) == ["custom"]


def test_get_client_raises_in_seed_mode(monkeypatch):
    monkeypatch.delenv("MONGO_URI", raising=False)
    db.close_client()
    with pytest.raises(RuntimeError):
        db.get_client()


def test_unknown_collection_rejected():
    with pytest.raises(KeyError):
        db.get_collection("nope")


def test_ensure_indexes_noop_in_seed_mode(monkeypatch):
    monkeypatch.delenv("MONGO_URI", raising=False)
    assert db.ensure_indexes() == {}


def test_ensure_indexes_creates_documented_indexes_in_mongo_mode(mongo_mode):
    created = db.ensure_indexes()
    database = mongo_mode.instances[0].databases["vantage"]
    for name, fields in db.INDEXES.items():
        assert database.collections[name].indexes == list(fields)
        assert created[name] == [f"{f}_1" for f in fields]
    assert set(db.INDEXES["accounts"]) == {"account_id", "billing_ref"}
    assert set(db.INDEXES["usage"]) == {"account_id", "period"}
    assert "device_uuid" in db.INDEXES["sites"] and "market_id" in db.INDEXES["sites"]


def test_find_documents_pushes_query_to_mongo_and_drops_none(mongo_mode):
    docs = db.find_documents("usage", {"account_id": None, "period": "2026-07"})
    assert docs == [{"query": {"period": "2026-07"}}]


def test_lifespan_closes_client_on_shutdown(mongo_mode):
    with TestClient(app) as client:
        assert client.get("/health").status_code == 200
        assert len(mongo_mode.instances) == 1
        assert mongo_mode.instances[0].databases["vantage"].collections["usage"].indexes
    assert mongo_mode.instances[0].closed is True


def test_lifespan_seed_mode_is_noop(monkeypatch):
    monkeypatch.delenv("MONGO_URI", raising=False)
    with TestClient(app) as client:
        assert client.get("/health").json() == {"status": "ok"}


# --- seed-mode query push-down must match the Python filters it replaces -----


def _python_filter(docs: list[dict[str, Any]], **filters: Any) -> list[dict[str, Any]]:
    out = docs
    for key, value in filters.items():
        if value:
            out = [d for d in out if d.get(key) == value]
    return out


def test_seed_find_documents_matches_python_filter():
    all_usage = db.all_documents("usage")
    assert db.find_documents("usage", {"period": "2026-07"}) == _python_filter(
        all_usage, period="2026-07"
    )
    account_id = next(r["account_id"] for r in all_usage if r.get("account_id"))
    assert db.find_documents("usage", {"account_id": account_id, "period": "2026-07"}) == (
        _python_filter(all_usage, account_id=account_id, period="2026-07")
    )
    assert db.find_documents("usage", {}) == all_usage
    assert db.find_documents("usage", None) == all_usage
    assert db.find_documents("usage", {"period": "1999-01"}) == []


def test_list_sites_push_down_matches_python_filter():
    sites = db.all_documents("sites")
    market = sites[0]["market_id"]
    state = sites[0]["lifecycle_state"]
    expected = [
        repository.enrich_site(s)
        for s in _python_filter(sites, market_id=market, lifecycle_state=state)
    ]
    assert repository.list_sites(market_id=market, lifecycle_state=state) == expected
    assert repository.list_sites(market_id="") == [repository.enrich_site(s) for s in sites]
    assert repository.list_sites(market_id="ZZZ") == []


def test_get_site_and_list_circuits_push_down():
    sites = db.all_documents("sites")
    assert repository.get_site(sites[-1]["device_uuid"]) == repository.enrich_site(sites[-1])
    assert repository.get_site("missing") is None
    circuits = db.all_documents("circuits")
    assert repository.list_circuits() == [repository.enrich_circuit(c) for c in circuits]
    assert repository.list_circuits(circuits[0]["circuit_id"]) == [
        repository.enrich_circuit(circuits[0])
    ]


def test_usage_records_and_unlinked_usage_match_python_filter():
    all_usage = db.all_documents("usage")
    assert invoice_service.usage_records(period="2026-07") == _python_filter(
        all_usage, period="2026-07"
    )
    assert invoice_service.usage_records() == all_usage
    unlinked = [r for r in all_usage if not r.get("account_id") and r.get("period") == "2026-07"]
    assert invoice_service.unlinked_usage(period="2026-07") == unlinked
    assert invoice_service.mediated_usage_mb(period="2026-07") == sum(
        int(r["usage_mb"]) for r in _python_filter(all_usage, period="2026-07")
    )


def test_accounts_by_id_matches_linear_find_account():
    index = invoice_service.accounts_by_id()
    for account in invoice_service.accounts():
        assert index[account["account_id"]] == invoice_service.find_account(account["account_id"])
    assert invoice_service.find_account("missing") is None
    assert "missing" not in index


# --- N+1 refactor: /billing/invoices output must be byte-for-byte unchanged ---


def test_billing_invoices_json_byte_for_byte_matches_fixture(client):
    response = client.get("/billing/invoices?period=2026-07")
    assert response.status_code == 200
    assert response.content == FIXTURE.read_bytes()


def test_billing_invoices_fixture_is_well_formed():
    payload = json.loads(FIXTURE.read_text())
    assert payload["count"] == len(payload["invoices"]) > 0
    assert all(i["period"] == "2026-07" for i in payload["invoices"])
