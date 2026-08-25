"""Meridian source data.

Flat ``KEY=value`` account records, CSV telemetry drops and a numeric status
code per resource. Everything is mapped onto ``oss.model`` here; the lifecycle
codes are widened to the five-state vocabulary, which Meridian never had names
for (it has no PLANNED or RESERVED resources).
"""

from __future__ import annotations

import csv
from decimal import Decimal
from pathlib import Path

from oss.model import Account, Circuit, Device, Location, Site, UsageRecord

DATA_ROOT = Path(__file__).resolve().parents[2] / "data" / "meridian"

LIFECYCLE_BY_CODE = {"1": "ACTIVE", "2": "MAINTENANCE", "3": "RETIRED"}
ROLE_BY_CODE = {"1": "PRIMARY", "2": "STANDBY", "3": "FAILOVER"}


def _rows(path: Path) -> list[dict[str, str]]:
    with path.open(newline="") as handle:
        return [dict(row) for row in csv.DictReader(handle)]


def _decimal(value: str) -> Decimal:
    return Decimal(str(value or "0"))


def _account_from_fields(fields: dict[str, str]) -> Account:
    return Account(
        account_id=fields.get("ACCT_ID", ""),
        billing_ref=fields.get("BILLING_REF", ""),
        legal_name=fields.get("CUST_NM", ""),
        tax_id=fields.get("TAX_ID", ""),
        service_address=fields.get("SVC_ADDR", ""),
        province=fields.get("PROVINCE", ""),
        plan_code=fields.get("PLAN_CD", ""),
        plan_monthly_fee=_decimal(fields.get("PLAN_FEE", "0")),
        included_gb=int(fields.get("INCLUDED_GB") or 0),
        previous_plan_fee=_decimal(fields.get("PREV_PLAN_FEE", "0")),
        plan_change_day=int(fields.get("PLAN_CHG_DAY") or 0),
        line_count=int(fields.get("LINE_CNT") or 1),
        promo_credit_amount=_decimal(fields.get("PROMO_AMT", "0")),
        promo_issued_on=fields.get("PROMO_DT") or None,
        suspension_start_day=int(fields.get("SUSP_START") or 0),
        suspension_end_day=int(fields.get("SUSP_END") or 0),
        prior_balance=_decimal(fields.get("PRIOR_BAL", "0")),
        prior_due_date=fields.get("PRIOR_DUE") or None,
        loyalty_discount_pct=_decimal(fields.get("LOYALTY_PCT", "0")),
        estate="meridian",
    )


def load_accounts(root: Path = DATA_ROOT) -> list[Account]:
    """The account master: one flat record per account under ``accounts/``."""
    accounts = []
    for path in sorted((root / "accounts").glob("*.rec")):
        fields = {}
        for raw in path.read_text().splitlines():
            key, sep, value = raw.partition("=")
            if sep:
                fields[key] = value
        accounts.append(_account_from_fields(fields))
    return accounts


def load_usage(root: Path = DATA_ROOT) -> list[UsageRecord]:
    return [
        UsageRecord(
            account_id=row["ACCT_ID"], period=row["PERIOD"], usage_mb=int(row["USAGE_MB"])
        )
        for row in _rows(root / "usage.csv")
    ]


def load_sites(root: Path = DATA_ROOT) -> list[Site]:
    return [
        Site(
            site_id=row["ASSET_ID"],
            name=row["SITE_NM"],
            market_id=row["REGION_CD"],
            lifecycle_state=LIFECYCLE_BY_CODE.get(row["STATUS_CD"], "ACTIVE"),
            total_capacity_mbps=int(row["TOTAL_CAP_MBPS"]),
            allocated_mbps=int(row["ALLOC_CAP_MBPS"]),
            maintenance_buffer_mbps=0,
            latitude=float(row["LAT"]),
            longitude=float(row["LON"]),
            tower_registration=row.get("TOWER_REG", ""),
        )
        for row in _rows(root / "sites.csv")
    ]


def load_circuits(root: Path = DATA_ROOT) -> list[Circuit]:
    return [
        Circuit(
            circuit_id=row["CIRCUIT_ID"],
            name=row["CIRCUIT_NM"],
            a_site_id=row["A_ASSET_ID"],
            z_site_id=row["Z_ASSET_ID"],
            capacity_mbps=int(row["CAP_MBPS"]),
            allocated_mbps=int(row["ALLOC_MBPS"]),
            role=ROLE_BY_CODE.get(row["ROLE_CD"], "PRIMARY"),
            lifecycle_state=LIFECYCLE_BY_CODE.get(row["STATUS_CD"], "ACTIVE"),
            maintenance_buffer_mbps=0,
        )
        for row in _rows(root / "circuits.csv")
    ]


def load_locations(root: Path = DATA_ROOT) -> list[Location]:
    return [
        Location(
            location_code=row["LOC_CD"],
            customer_name=row["CUST_NM"],
            location_name=row["LOC_NM"],
            market_id=row["MARKET_CD"],
            total_capacity_mbps=int(row["TOTAL_CAP_MBPS"]),
            allocated_mbps=int(row["ALLOC_CAP_MBPS"]),
            maintenance_buffer_mbps=0,
        )
        for row in _rows(root / "locations.csv")
    ]


def load_devices(root: Path = DATA_ROOT) -> list[Device]:
    return [
        Device(
            device_name=row["device_name"],
            market_id=row["region"],
            role=row["role"],
            mgmt_ip=row["mgmt_ip"],
            external_bgp=row.get("external_bgp") == "1",
            site_id=row.get("site_cd", ""),
        )
        for row in _rows(root / "devices.csv")
    ]
