"""Normalised records shared by both estates.

Meridian keys accounts by ``ACCT_ID`` and sites by numeric ``ASSET_ID``;
Vantage keys them by ``account_id`` and ``device_uuid``. Both books join on
``billing_ref`` for accounts and on the market/region code for the network, so
the adapters map either source onto these records and everything downstream
reads one shape.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from decimal import Decimal


@dataclass(frozen=True)
class Account:
    account_id: str
    billing_ref: str
    legal_name: str
    province: str
    plan_code: str
    plan_monthly_fee: Decimal
    included_gb: int
    tax_id: str = ""
    service_address: str = ""
    previous_plan_fee: Decimal = Decimal("0")
    plan_change_day: int = 0
    line_count: int = 1
    promo_credit_amount: Decimal = Decimal("0")
    promo_issued_on: str | None = None
    suspension_start_day: int = 0
    suspension_end_day: int = 0
    prior_balance: Decimal = Decimal("0")
    prior_due_date: str | None = None
    loyalty_discount_pct: Decimal = Decimal("0")
    estate: str = ""


@dataclass(frozen=True)
class UsageRecord:
    account_id: str
    period: str
    usage_mb: int
    device_id: str = ""


@dataclass(frozen=True)
class Site:
    site_id: str
    name: str
    market_id: str
    lifecycle_state: str
    total_capacity_mbps: int = 0
    allocated_mbps: int = 0
    maintenance_buffer_mbps: int = 0
    latitude: float = 0.0
    longitude: float = 0.0
    tower_registration: str = ""


@dataclass(frozen=True)
class Circuit:
    circuit_id: str
    name: str
    a_site_id: str
    z_site_id: str
    capacity_mbps: int
    allocated_mbps: int
    role: str
    lifecycle_state: str
    maintenance_buffer_mbps: int = 0


@dataclass(frozen=True)
class Location:
    location_code: str
    customer_name: str
    location_name: str
    market_id: str
    total_capacity_mbps: int
    allocated_mbps: int
    maintenance_buffer_mbps: int = 0


@dataclass(frozen=True)
class Device:
    device_name: str
    market_id: str
    role: str
    mgmt_ip: str
    external_bgp: bool = False
    site_id: str = ""
    device_uuid: str = ""


@dataclass
class Invoice:
    account_id: str
    billing_ref: str
    period: str
    province: str
    estate: str
    usage_mb: int
    included_gb: int
    overage_mb: int
    overage_gb: int
    plan_charge: Decimal
    line_discount: Decimal
    recurring: Decimal
    overage_charges: Decimal
    suspension_credit: Decimal
    promo_credit: Decimal
    late_fee: Decimal
    subtotal: Decimal
    loyalty_discount: Decimal
    federal_tax_label: str
    federal_tax: Decimal
    provincial_tax_label: str
    provincial_tax: Decimal
    total: Decimal
    legal_name: str = ""
    rules: dict = field(default_factory=dict)
