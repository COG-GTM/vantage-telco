"""Vantage source data.

JSON documents mirroring the Mongo collections, keyed by ``device_uuid`` and
carrying an explicit five-state lifecycle and a maintenance buffer per record.
"""

from __future__ import annotations

import json
from decimal import Decimal
from pathlib import Path
from typing import Any

from oss.model import Account, Circuit, Device, Location, Site, UsageRecord

DATA_ROOT = Path(__file__).resolve().parents[2] / "data" / "vantage"


def _documents(root: Path, name: str) -> list[dict[str, Any]]:
    with (root / f"{name}.json").open() as handle:
        return json.load(handle)


def _decimal(value: Any) -> Decimal:
    return Decimal(str(value or 0))


def load_accounts(root: Path = DATA_ROOT) -> list[Account]:
    return [
        Account(
            account_id=doc["account_id"],
            billing_ref=doc.get("billing_ref", ""),
            legal_name=doc.get("legal_name", ""),
            tax_id=doc.get("tax_id", ""),
            service_address=doc.get("service_address", ""),
            province=doc.get("province", ""),
            plan_code=doc.get("plan_code", ""),
            plan_monthly_fee=_decimal(doc["plan_monthly_fee"]),
            included_gb=int(doc["included_gb"]),
            previous_plan_fee=_decimal(doc.get("previous_plan_fee")),
            plan_change_day=int(doc.get("plan_change_day") or 0),
            line_count=int(doc.get("line_count") or 1),
            promo_credit_amount=_decimal(doc.get("promo_credit_amount")),
            promo_issued_on=doc.get("promo_issued_on"),
            suspension_start_day=int(doc.get("suspension_start_day") or 0),
            suspension_end_day=int(doc.get("suspension_end_day") or 0),
            prior_balance=_decimal(doc.get("prior_balance")),
            prior_due_date=doc.get("prior_due_date"),
            loyalty_discount_pct=_decimal(doc.get("loyalty_discount_pct")),
            estate="vantage",
        )
        for doc in _documents(root, "accounts")
    ]


def load_usage(root: Path = DATA_ROOT) -> list[UsageRecord]:
    return [
        UsageRecord(
            account_id=doc.get("account_id") or "",
            period=doc["period"],
            usage_mb=int(doc["usage_mb"]),
            device_id=doc.get("device_uuid", ""),
        )
        for doc in _documents(root, "usage")
    ]


def load_sites(root: Path = DATA_ROOT) -> list[Site]:
    return [
        Site(
            site_id=doc["device_uuid"],
            name=doc["name"],
            market_id=doc["market_id"],
            lifecycle_state=doc["lifecycle_state"],
            total_capacity_mbps=int(doc.get("total_capacity_mbps", 0)),
            allocated_mbps=int(doc.get("allocated_mbps", 0)),
            maintenance_buffer_mbps=int(doc.get("maintenance_buffer_mbps", 0)),
            latitude=float(doc.get("latitude", 0.0)),
            longitude=float(doc.get("longitude", 0.0)),
            tower_registration=doc.get("tower_registration") or "",
        )
        for doc in _documents(root, "sites")
    ]


def load_circuits(root: Path = DATA_ROOT) -> list[Circuit]:
    return [
        Circuit(
            circuit_id=doc["circuit_id"],
            name=doc["name"],
            a_site_id=doc["a_device_uuid"],
            z_site_id=doc["z_device_uuid"],
            capacity_mbps=int(doc["capacity_mbps"]),
            allocated_mbps=int(doc["allocated_mbps"]),
            role=doc["role"],
            lifecycle_state=doc["lifecycle_state"],
            maintenance_buffer_mbps=int(doc.get("maintenance_buffer_mbps", 0)),
        )
        for doc in _documents(root, "circuits")
    ]


def load_locations(root: Path = DATA_ROOT) -> list[Location]:
    return [
        Location(
            location_code=doc["location_code"],
            customer_name=doc["customer_name"],
            location_name=doc["location_name"],
            market_id=doc["market_id"],
            total_capacity_mbps=int(doc["total_capacity_mbps"]),
            allocated_mbps=int(doc["allocated_mbps"]),
            maintenance_buffer_mbps=int(doc.get("maintenance_buffer_mbps", 0)),
        )
        for doc in _documents(root, "locations")
    ]


def load_devices(root: Path = DATA_ROOT) -> list[Device]:
    return [
        Device(
            device_name=doc["device_name"],
            market_id=doc["market_id"],
            role=doc["role"],
            mgmt_ip=doc["mgmt_ip"],
            external_bgp=bool(doc.get("external_bgp")),
            device_uuid=doc.get("device_uuid", ""),
        )
        for doc in _documents(root, "devices")
    ]
