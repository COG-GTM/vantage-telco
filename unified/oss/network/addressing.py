"""Management addressing.

Both estates number the management plane out of 10.20.0.0/16 with
10.20.250.0/24 held as the growth pool, and both keep generated artifacts
(routing, firewall, DNS, monitoring) that reference those addresses. Meridian
only ever reported on the assignment file; the reference and orphan checks come
from Vantage and are run against either estate's device list.
"""

from __future__ import annotations

import ipaddress
import json
import re
from collections import Counter
from collections.abc import Iterable, Sequence
from pathlib import Path
from typing import Any

from oss.model import Device

MANAGEMENT_SUPERNET = ipaddress.ip_network("10.20.0.0/16")
GROWTH_POOL = ipaddress.ip_network("10.20.250.0/24")
CONFIG_ROOT = Path(__file__).resolve().parent / "configs"
IPV4_PATTERN = re.compile(r"\b(?:\d{1,3}\.){3}\d{1,3}\b")


def address_plan() -> dict[str, Any]:
    with (CONFIG_ROOT / "address_plan.json").open() as handle:
        return json.load(handle)


def in_supernet(address: str) -> bool:
    return ipaddress.ip_address(address) in MANAGEMENT_SUPERNET


def in_growth_pool(address: str) -> bool:
    return ipaddress.ip_address(address) in GROWTH_POOL


def assigned_addresses(devices: Iterable[Device]) -> list[str]:
    return sorted({d.mgmt_ip for d in devices})


def duplicate_addresses(devices: Iterable[Device]) -> dict[str, list[str]]:
    by_address: dict[str, list[str]] = {}
    for device in devices:
        by_address.setdefault(device.mgmt_ip, []).append(device.device_name)
    return {ip: names for ip, names in by_address.items() if len(names) > 1}


def subnet_usage(devices: Iterable[Device]) -> dict[str, int]:
    counts = Counter(
        f"10.20.{int(d.mgmt_ip.split('.')[2])}.0/24" for d in devices if in_supernet(d.mgmt_ip)
    )
    return dict(sorted(counts.items()))


def config_files() -> list[Path]:
    return sorted(p for p in CONFIG_ROOT.rglob("*") if p.is_file())


def references(address: str) -> list[Path]:
    return [path for path in config_files() if address in path.read_text()]


def referenced_addresses() -> dict[str, int]:
    counts: Counter = Counter()
    for path in config_files():
        counts.update(IPV4_PATTERN.findall(path.read_text()))
    return dict(counts)


def orphaned_references(devices: Sequence[Device]) -> dict[str, int]:
    """Addresses a config file points at that no device owns."""
    assigned = set(assigned_addresses(devices)) | {
        "10.20.0.1",  # management-plane default gateway
        str(MANAGEMENT_SUPERNET.network_address),
        str(GROWTH_POOL.network_address),
    }
    return {
        ip: n for ip, n in referenced_addresses().items()
        if ip not in assigned and in_supernet(ip)
    }


def summary(devices: Sequence[Device]) -> dict[str, Any]:
    counts = referenced_addresses()
    return {
        "management_supernet": str(MANAGEMENT_SUPERNET),
        "growth_pool": str(GROWTH_POOL),
        "device_count": len(devices),
        "assigned_addresses": len(assigned_addresses(devices)),
        "duplicate_addresses": duplicate_addresses(devices),
        "subnet_usage": subnet_usage(devices),
        "config_files": len(config_files()),
        "address_references": sum(counts.values()),
        "external_bgp_devices": [d.device_name for d in devices if d.external_bgp],
        "growth_pool_allocations": [d.mgmt_ip for d in devices if in_growth_pool(d.mgmt_ip)],
    }
