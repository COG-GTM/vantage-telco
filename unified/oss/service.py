"""Estate services.

Binds a source book (via an adapter) to a policy and runs the shared engine
over it. ``vantage-report`` reads the Vantage book, since it is the same
estate's data rated for the archived NOC report.
"""

from __future__ import annotations

from collections.abc import Iterable
from decimal import Decimal
from functools import cache
from typing import Any

from oss.adapters import meridian as meridian_adapter
from oss.adapters import vantage as vantage_adapter
from oss.billing.invoice import compute_invoice, invoice_dict
from oss.inventory.capacity import site_capacity
from oss.inventory.circuits import active_capacity_mbps, active_count
from oss.inventory.locations import list_locations
from oss.model import Account, Circuit, Device, Invoice, Location, Site, UsageRecord
from oss.network import addressing
from oss.policy import EstatePolicy, estate

ADAPTERS = {
    "meridian": meridian_adapter,
    "vantage": vantage_adapter,
    "vantage-report": vantage_adapter,
}


def adapter_for(name: str):
    try:
        return ADAPTERS[name]
    except KeyError:
        raise KeyError(f"no source adapter for estate {name!r}") from None


class Estate:
    """One estate: its source book plus the policy its rules run under."""

    def __init__(self, name: str) -> None:
        self.policy: EstatePolicy = estate(name)
        self.name = name
        self._adapter = adapter_for(name)
        self._cache: dict[str, Any] = {}

    def _load(self, collection: str) -> Any:
        if collection not in self._cache:
            loaders = {
                "accounts": self._adapter.load_accounts,
                "usage": self._adapter.load_usage,
                "sites": self._adapter.load_sites,
                "circuits": self._adapter.load_circuits,
                "locations": self._adapter.load_locations,
                "devices": self._adapter.load_devices,
            }
            self._cache[collection] = loaders[collection]()
        return self._cache[collection]

    # -- source data ----------------------------------------------------
    def accounts(self) -> list[Account]:
        return self._load("accounts")

    def usage(self) -> list[UsageRecord]:
        return self._load("usage")

    def sites(self) -> list[Site]:
        return self._load("sites")

    def circuits(self) -> list[Circuit]:
        return self._load("circuits")

    def locations(self) -> list[Location]:
        return self._load("locations")

    def devices(self) -> list[Device]:
        return self._load("devices")

    def find_account(self, account_id: str) -> Account | None:
        for account in self.accounts():
            if account.account_id == account_id:
                return account
        return None

    # -- billing --------------------------------------------------------
    def invoices(
        self, period: str | None = None, account_id: str | None = None
    ) -> list[Invoice]:
        out = []
        for usage in self.usage():
            if period and usage.period != period:
                continue
            if account_id and usage.account_id != account_id:
                continue
            account = self.find_account(usage.account_id) if usage.account_id else None
            if account is None:
                continue
            out.append(compute_invoice(account, usage, self.policy))
        return out

    def invoice_records(self, period: str | None = None) -> list[dict[str, Any]]:
        return [invoice_dict(i) for i in self.invoices(period=period)]

    def revenue_total(self, period: str | None = None) -> Decimal:
        return sum((i.total for i in self.invoices(period=period)), Decimal("0"))

    def unlinked_usage(self, period: str | None = None) -> list[UsageRecord]:
        """Mediated usage carrying no billing account. Never invoiced."""
        known = {a.account_id for a in self.accounts()}
        return [
            u for u in self.usage()
            if (not u.account_id or u.account_id not in known)
            and (period is None or u.period == period)
        ]

    # -- inventory ------------------------------------------------------
    def site_records(self, market_id: str | None = None) -> list[dict[str, Any]]:
        records = []
        for site in self.sites():
            if market_id and site.market_id != market_id:
                continue
            record = dict(site.__dict__)
            record.update(site_capacity(site, self.policy.inventory))
            records.append(record)
        return records

    def circuit_summary(self) -> dict[str, Any]:
        circuits = self.circuits()
        return {
            "estate": self.name,
            "circuits": len(circuits),
            "active_circuits": active_count(circuits, self.policy.inventory),
            "active_capacity_mbps": active_capacity_mbps(circuits, self.policy.inventory),
            "counts_redundant_roles": self.policy.inventory.active_circuit_roles is None,
        }

    def capacity(
        self, requested_mbps: int = 0, market_id: str | None = None
    ) -> list[dict[str, Any]]:
        return list_locations(
            self.locations(),
            self.policy.inventory,
            requested_mbps=requested_mbps,
            market_id=market_id,
        )

    # -- network --------------------------------------------------------
    def addressing_summary(self) -> dict[str, Any]:
        return addressing.summary(self.devices())

    def orphaned_references(self) -> dict[str, int]:
        return addressing.orphaned_references(self.devices())


@cache
def get_estate(name: str) -> Estate:
    return Estate(name)


def estate_names() -> Iterable[str]:
    return ADAPTERS.keys()
