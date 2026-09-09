"""Data access.

Production runs against MongoDB (``MONGO_URI`` / ``MONGO_URI_FILE``, see
:mod:`app.settings`). For local development and the
test suite the same collections are served from the JSON documents under
``data/seed``, so nothing here needs a running database.
"""

from __future__ import annotations

import json
from collections.abc import Iterable
from functools import cache
from pathlib import Path
from typing import Any

from app.settings import get_setting

SEED_DIR = Path(__file__).resolve().parent.parent / "data" / "seed"

COLLECTIONS = {
    "sites": "sites.json",
    "circuits": "circuits.json",
    "accounts": "accounts.json",
    "usage": "usage.json",
    "devices": "devices.json",
    "locations": "locations.json",
}

REQUIRED_INDEXES: dict[str, list[str]] = {
    "accounts": ["account_id", "billing_ref"],
    "usage": ["account_id", "period"],
    "sites": ["device_uuid", "market_id"],
    "devices": ["device_uuid", "market_id"],
    "locations": ["market_id"],
}

_client: Any = None


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
    for key, value in query.items():
        if isinstance(value, dict) and "$in" in value:
            if doc.get(key) not in value["$in"]:
                return False
        elif doc.get(key) != value:
            return False
    return True


@cache
def _load_seed(name: str) -> SeedCollection:
    with (SEED_DIR / COLLECTIONS[name]).open() as handle:
        return SeedCollection(json.load(handle))


def get_collection(name: str):
    """Return the named collection, from Mongo when configured, else the seed."""
    if name not in COLLECTIONS:
        raise KeyError(f"unknown collection: {name}")
    if not mongo_enabled():
        return _load_seed(name)
    return mongo_client()[mongo_db_name()][name]


def mongo_client() -> Any:
    """Process-wide pymongo client, created on first use so pooling is reused."""
    global _client
    if _client is None:
        from pymongo import MongoClient  # imported lazily: unused in seed mode

        _client = MongoClient(mongo_uri())
    return _client


def mongo_uri() -> str | None:
    return get_setting("MONGO_URI")


def mongo_db_name() -> str:
    return get_setting("MONGO_DB") or "vantage"


def close_client() -> None:
    global _client
    if _client is not None:
        _client.close()
        _client = None


def mongo_enabled() -> bool:
    return mongo_uri() is not None


def find_documents(name: str, query: dict[str, Any]) -> list[dict[str, Any]]:
    collection = get_collection(name)
    if mongo_enabled():
        return list(collection.find(query, {"_id": False}))
    return list(collection.find(query))


def all_documents(name: str) -> list[dict[str, Any]]:
    return find_documents(name, {})


def ensure_indexes() -> None:
    """Create the indexes the query paths rely on. No-op in seed mode."""
    if not mongo_enabled():
        return
    for name, fields in REQUIRED_INDEXES.items():
        collection = get_collection(name)
        for field in fields:
            collection.create_index(field)
