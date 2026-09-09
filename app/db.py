"""Data access.

Production runs against MongoDB (``MONGO_URI``). For local development and the
test suite the same collections are served from the JSON documents under
``data/seed``, so nothing here needs a running database.

In Mongo mode a single ``MongoClient`` is created lazily and reused for the
lifetime of the process so pymongo's connection pool is shared across requests.
"""

from __future__ import annotations

import json
import threading
from collections.abc import Iterable
from functools import cache
from pathlib import Path
from typing import Any

from app.config import setting

SEED_DIR = Path(__file__).resolve().parent.parent / "data" / "seed"

COLLECTIONS = {
    "sites": "sites.json",
    "circuits": "circuits.json",
    "accounts": "accounts.json",
    "usage": "usage.json",
    "devices": "devices.json",
    "locations": "locations.json",
}

# Indexes required for the query push-down in Mongo mode: collection -> fields.
INDEXES: dict[str, tuple[str, ...]] = {
    "accounts": ("account_id", "billing_ref"),
    "usage": ("account_id", "period"),
    "sites": ("device_uuid", "market_id"),
    "devices": ("device_uuid",),
    "locations": ("market_id",),
}


class SeedCollection:
    """Read-only stand-in for a Mongo collection backed by a seed file."""

    def __init__(self, documents: list[dict[str, Any]]) -> None:
        self._documents = documents

    def find(self, query: dict[str, Any] | None = None) -> Iterable[dict[str, Any]]:
        for doc in self._documents:
            if _matches(doc, query or {}):
                yield dict(doc)

    def find_one(self, query: dict[str, Any] | None = None) -> dict[str, Any] | None:
        for doc in self.find(query):
            return doc
        return None

    def count_documents(self, query: dict[str, Any] | None = None) -> int:
        return sum(1 for _ in self.find(query))


def _matches(doc: dict[str, Any], query: dict[str, Any]) -> bool:
    return all(doc.get(key) == value for key, value in query.items())


@cache
def _load_seed(name: str) -> SeedCollection:
    with (SEED_DIR / COLLECTIONS[name]).open() as handle:
        return SeedCollection(json.load(handle))


_client: Any = None
_client_uri: str | None = None
_client_lock = threading.Lock()


def mongo_uri() -> str | None:
    return setting("MONGO_URI") or None


def get_client() -> Any:
    """Return the process-wide ``MongoClient``, creating it on first use."""
    global _client, _client_uri
    uri = mongo_uri()
    if uri is None:
        raise RuntimeError("MONGO_URI is not set; running in seed-file mode")
    with _client_lock:
        if _client is None or _client_uri != uri:
            if _client is not None:
                _client.close()
            from pymongo import MongoClient  # imported lazily: unused in seed mode

            _client = MongoClient(uri)
            _client_uri = uri
        return _client


def close_client() -> None:
    """Close the shared client (FastAPI shutdown). Safe to call in seed mode."""
    global _client, _client_uri
    with _client_lock:
        if _client is not None:
            _client.close()
        _client = None
        _client_uri = None


def get_collection(name: str):
    """Return the named collection, from Mongo when configured, else the seed."""
    if name not in COLLECTIONS:
        raise KeyError(f"unknown collection: {name}")
    if mongo_uri() is None:
        return _load_seed(name)
    return get_client()[setting("MONGO_DB", "vantage")][name]


def ensure_indexes() -> dict[str, list[str]]:
    """Create the indexes in ``INDEXES`` when in Mongo mode; no-op in seed mode.

    Returns the index names created per collection (empty in seed mode).
    """
    if mongo_uri() is None:
        return {}
    created: dict[str, list[str]] = {}
    for name, fields in INDEXES.items():
        collection = get_collection(name)
        created[name] = [collection.create_index(field) for field in fields]
    return created


def find_documents(name: str, query: dict[str, Any] | None = None) -> list[dict[str, Any]]:
    """Return documents matching ``query``, filtered by the datastore.

    ``None`` values are dropped so optional filters can be passed straight
    through: ``find_documents("usage", {"account_id": None, "period": p})``
    only constrains ``period``.
    """
    filters = {key: value for key, value in (query or {}).items() if value is not None}
    return list(get_collection(name).find(filters))


def all_documents(name: str) -> list[dict[str, Any]]:
    return find_documents(name, {})
