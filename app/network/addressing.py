"""Management addressing.

Every Vantage device gets a management address out of ``MANAGEMENT_SUPERNET``.
The generated artifacts under ``app/network/configs`` (routing, firewall, DNS,
monitoring) all reference these addresses and are expected to stay in sync with
``data/seed/devices.json``.

The supernet and the reserved ranges come from telco-rules (DECISIONS.md D-10).
``10.20.250.0/24`` is reserved for the planned aggregation build-out (the
``agg-sw-growth-*`` switches sit in it) and ``10.20.251.0/24`` for the lab;
neither is free pool. ``GROWTH_POOL`` keeps its name for existing callers.
"""

from __future__ import annotations

import ipaddress
import json
import re
from pathlib import Path
from typing import Any, Dict, Iterable, List

import telco_rules

from app.db import all_documents

MANAGEMENT_SUPERNET = ipaddress.ip_network(telco_rules.MGMT_SUPERNET)
GROWTH_POOL = ipaddress.ip_network(telco_rules.PLANNED_BUILDOUT_RESERVE)

CONFIG_ROOT = Path(__file__).resolve().parent / "configs"
IPV4_PATTERN = re.compile(r"\b(?:\d{1,3}\.){3}\d{1,3}\b")


def devices() -> List[Dict[str, Any]]:
    return all_documents("devices")


def address_plan() -> Dict[str, Any]:
    with (CONFIG_ROOT / "address_plan.json").open() as handle:
        return json.load(handle)


def assigned_addresses() -> List[str]:
    return sorted({d["mgmt_ip"] for d in devices()})


def external_bgp_devices() -> List[Dict[str, Any]]:
    return [d for d in devices() if d.get("external_bgp")]


def in_supernet(address: str) -> bool:
    return telco_rules.in_mgmt_supernet(address)


def in_growth_pool(address: str) -> bool:
    return telco_rules.ip_in_cidr(address, telco_rules.PLANNED_BUILDOUT_RESERVE)


def reserved_ranges() -> List[Dict[str, str]]:
    return [{"cidr": r.cidr, "purpose": r.purpose} for r in telco_rules.reserved_ranges()]


def reserved_purpose(address: str) -> str:
    """Purpose of the reserved range holding ``address``, or "" if none."""
    return telco_rules.reserved_purpose(address)


def config_files() -> List[Path]:
    return sorted(p for p in CONFIG_ROOT.rglob("*") if p.is_file())


def references(address: str) -> List[Path]:
    """Every config file that mentions the given address."""
    hits = []
    for path in config_files():
        if address in path.read_text():
            hits.append(path)
    return hits


def referenced_addresses() -> Dict[str, int]:
    counts: Dict[str, int] = {}
    for path in config_files():
        for match in IPV4_PATTERN.findall(path.read_text()):
            counts[match] = counts.get(match, 0) + 1
    return counts


def orphaned_references() -> Dict[str, int]:
    """Addresses referenced by a config file but assigned to no device."""
    assigned = set(assigned_addresses()) | {
        "10.20.0.1",  # default gateway of the management plane
        str(MANAGEMENT_SUPERNET.network_address),
        str(GROWTH_POOL.network_address),
    }
    return {ip: n for ip, n in referenced_addresses().items()
            if ip not in assigned and in_supernet(ip)}


def summary() -> Dict[str, Any]:
    counts = referenced_addresses()
    return {
        "management_supernet": str(MANAGEMENT_SUPERNET),
        "growth_pool": str(GROWTH_POOL),
        "device_count": len(devices()),
        "assigned_addresses": len(assigned_addresses()),
        "config_files": len(config_files()),
        "address_references": sum(counts.values()),
        "external_bgp_devices": [d["device_name"] for d in external_bgp_devices()],
        "growth_pool_allocations": [d["mgmt_ip"] for d in devices() if in_growth_pool(d["mgmt_ip"])],
        "reserved_ranges": reserved_ranges(),
        "reserved_range_allocations": [d["mgmt_ip"] for d in devices() if reserved_purpose(d["mgmt_ip"])],
    }


def iter_addresses(source: Iterable[Dict[str, Any]]) -> Iterable[str]:
    for device in source:
        yield device["mgmt_ip"]
