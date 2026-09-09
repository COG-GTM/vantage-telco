from __future__ import annotations

from typing import Any

from app.db import find_documents
from app.inventory.capacity import available_capacity, site_capacity


def list_sites(
    market_id: str | None = None, lifecycle_state: str | None = None
) -> list[dict[str, Any]]:
    sites = find_documents(
        "sites",
        {"market_id": market_id or None, "lifecycle_state": lifecycle_state or None},
    )
    return [enrich_site(s) for s in sites]


def get_site(device_uuid: str) -> dict[str, Any] | None:
    for site in find_documents("sites", {"device_uuid": device_uuid}):
        return enrich_site(site)
    return None


def enrich_site(site: dict[str, Any]) -> dict[str, Any]:
    enriched = dict(site)
    capacity = site_capacity(site)
    enriched["available_mbps"] = capacity["available_mbps"]
    enriched["utilization_pct"] = capacity["utilization_pct"]
    return enriched


def list_circuits(circuit_id: str | None = None) -> list[dict[str, Any]]:
    circuits = find_documents("circuits", {"circuit_id": circuit_id or None})
    return [enrich_circuit(c) for c in circuits]


def enrich_circuit(circuit: dict[str, Any]) -> dict[str, Any]:
    enriched = dict(circuit)
    enriched["available_mbps"] = available_capacity(
        int(circuit.get("capacity_mbps", 0)),
        int(circuit.get("allocated_mbps", 0)),
        int(circuit.get("maintenance_buffer_mbps", 0)),
    )
    return enriched
