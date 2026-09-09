"""Data access.

Production runs against MongoDB (``MONGO_URI``). For local development and the
test suite the same collections are served from the JSON documents under
``data/seed``, so nothing here needs a running database.
"""

from __future__ import annotations

import json
import os
from collections.abc import Iterable
from functools import cache
from pathlib import Path
from typing import Any

SEED_DIR = Path(__file__).resolve().parent.parent / "data" / "seed"

COLLECTIONS = {
    "sites": "sites.json",
    "circuits": "circuits.json",
    "accounts": "accounts.json",
    "usage": "usage.json",
    "devices": "devices.json",
    "locations": "locations.json",
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


def get_collection(name: str):
    """Return the named collection, from Mongo when configured, else the seed."""
    if name not in COLLECTIONS:
        raise KeyError(f"unknown collection: {name}")
    uri = os.environ.get("MONGO_URI")
    if not uri:
        return _load_seed(name)
    from pymongo import MongoClient  # imported lazily: unused in seed mode

    client: Any = MongoClient(uri)
    return client[os.environ.get("MONGO_DB", "vantage")][name]


def all_documents(name: str) -> list[dict[str, Any]]:
    return list(get_collection(name).find({}))
