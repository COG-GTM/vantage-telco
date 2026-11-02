from __future__ import annotations

from typing import Any, Dict, List, Optional

from app.db import all_documents
from app.inventory.capacity import available_capacity, maintenance_buffer_mbps, site_capacity


def list_sites(market_id: Optional[str] = None, lifecycle_state: Optional[str] = None) -> List[Dict[str, Any]]:
    sites = all_documents("sites")
    if market_id:
        sites = [s for s in sites if s["market_id"] == market_id]
    if lifecycle_state:
        sites = [s for s in sites if s["lifecycle_state"] == lifecycle_state]
    return [enrich_site(s) for s in sites]


def get_site(device_uuid: str) -> Optional[Dict[str, Any]]:
    for site in all_documents("sites"):
        if site["device_uuid"] == device_uuid:
            return enrich_site(site)
    return None


def enrich_site(site: Dict[str, Any]) -> Dict[str, Any]:
    enriched = dict(site)
    capacity = site_capacity(site)
    enriched["maintenance_buffer_mbps"] = capacity["maintenance_buffer_mbps"]
    enriched["available_mbps"] = capacity["available_mbps"]
    enriched["utilization_pct"] = capacity["utilization_pct"]
    return enriched


def list_circuits(circuit_id: Optional[str] = None) -> List[Dict[str, Any]]:
    circuits = all_documents("circuits")
    if circuit_id:
        circuits = [c for c in circuits if c["circuit_id"] == circuit_id]
    return [enrich_circuit(c) for c in circuits]


def enrich_circuit(circuit: Dict[str, Any]) -> Dict[str, Any]:
    enriched = dict(circuit)
    total = int(circuit.get("capacity_mbps", 0))
    enriched["maintenance_buffer_mbps"] = maintenance_buffer_mbps(total)
    enriched["available_mbps"] = available_capacity(
        total,
        int(circuit.get("allocated_mbps", 0)),
        enriched["maintenance_buffer_mbps"],
    )
    return enriched
