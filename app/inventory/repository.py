from __future__ import annotations

from typing import Any

from app.db import all_documents
from app.inventory.capacity import available_capacity, site_capacity


def list_sites(
    market_id: str | None = None, lifecycle_state: str | None = None
) -> list[dict[str, Any]]:
    sites = all_documents("sites")
    if market_id:
        sites = [s for s in sites if s["market_id"] == market_id]
    if lifecycle_state:
        sites = [s for s in sites if s["lifecycle_state"] == lifecycle_state]
    return [enrich_site(s) for s in sites]


def get_site(device_uuid: str) -> dict[str, Any] | None:
    for site in all_documents("sites"):
        if site["device_uuid"] == device_uuid:
            return enrich_site(site)
    return None


def enrich_site(site: dict[str, Any]) -> dict[str, Any]:
    enriched = dict(site)
    capacity = site_capacity(site)
    enriched["available_mbps"] = capacity["available_mbps"]
    enriched["utilization_pct"] = capacity["utilization_pct"]
    return enriched


def list_circuits(circuit_id: str | None = None) -> list[dict[str, Any]]:
    circuits = all_documents("circuits")
    if circuit_id:
        circuits = [c for c in circuits if c["circuit_id"] == circuit_id]
    return [enrich_circuit(c) for c in circuits]


def enrich_circuit(circuit: dict[str, Any]) -> dict[str, Any]:
    enriched = dict(circuit)
    enriched["available_mbps"] = available_capacity(
        int(circuit.get("capacity_mbps", 0)),
        int(circuit.get("allocated_mbps", 0)),
        int(circuit.get("maintenance_buffer_mbps", 0)),
    )
    return enriched
