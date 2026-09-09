"""Management addressing.

Every Vantage device gets a management address out of ``MANAGEMENT_SUPERNET``.
The generated artifacts under ``app/network/configs`` (routing, firewall, DNS,
monitoring) all reference these addresses and are expected to stay in sync with
``data/seed/devices.json``.
"""

from __future__ import annotations

import ipaddress
import json
import re
from collections.abc import Iterable
from pathlib import Path
from typing import Any

from app.db import all_documents

MANAGEMENT_SUPERNET = ipaddress.ip_network("10.20.0.0/16")
GROWTH_POOL = ipaddress.ip_network("10.20.250.0/24")

CONFIG_ROOT = Path(__file__).resolve().parent / "configs"
IPV4_PATTERN = re.compile(r"\b(?:\d{1,3}\.){3}\d{1,3}\b")


def devices() -> list[dict[str, Any]]:
    return all_documents("devices")


def address_plan() -> dict[str, Any]:
    with (CONFIG_ROOT / "address_plan.json").open() as handle:
        return json.load(handle)


def assigned_addresses() -> list[str]:
    return sorted({d["mgmt_ip"] for d in devices()})


def external_bgp_devices() -> list[dict[str, Any]]:
    return [d for d in devices() if d.get("external_bgp")]


def in_supernet(address: str) -> bool:
    return ipaddress.ip_address(address) in MANAGEMENT_SUPERNET


def in_growth_pool(address: str) -> bool:
    return ipaddress.ip_address(address) in GROWTH_POOL


def config_files() -> list[Path]:
    return sorted(p for p in CONFIG_ROOT.rglob("*") if p.is_file())


def references(address: str) -> list[Path]:
    """Every config file that mentions the given address."""
    hits = []
    for path in config_files():
        if address in path.read_text():
            hits.append(path)
    return hits


def referenced_addresses() -> dict[str, int]:
    counts: dict[str, int] = {}
    for path in config_files():
        for match in IPV4_PATTERN.findall(path.read_text()):
            counts[match] = counts.get(match, 0) + 1
    return counts


def orphaned_references() -> dict[str, int]:
    """Addresses referenced by a config file but assigned to no device."""
    assigned = set(assigned_addresses()) | {
        "10.20.0.1",  # default gateway of the management plane
        str(MANAGEMENT_SUPERNET.network_address),
        str(GROWTH_POOL.network_address),
    }
    return {
        ip: n for ip, n in referenced_addresses().items() if ip not in assigned and in_supernet(ip)
    }


def summary() -> dict[str, Any]:
    counts = referenced_addresses()
    return {
        "management_supernet": str(MANAGEMENT_SUPERNET),
        "growth_pool": str(GROWTH_POOL),
        "device_count": len(devices()),
        "assigned_addresses": len(assigned_addresses()),
        "config_files": len(config_files()),
        "address_references": sum(counts.values()),
        "external_bgp_devices": [d["device_name"] for d in external_bgp_devices()],
        "growth_pool_allocations": [
            d["mgmt_ip"] for d in devices() if in_growth_pool(d["mgmt_ip"])
        ],
    }


def iter_addresses(source: Iterable[dict[str, Any]]) -> Iterable[str]:
    for device in source:
        yield device["mgmt_ip"]
