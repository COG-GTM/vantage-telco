"""HTTP surface.

Every route takes an ``estate`` so the same endpoint answers for Meridian
terms, Vantage terms, or the archived report's terms.
"""

from __future__ import annotations

from typing import Any

from fastapi import FastAPI, HTTPException, Query

from oss.billing.invoice import invoice_dict, rule_summary
from oss.policy import ESTATES
from oss.service import get_estate
from tools.parity import compare

app = FastAPI(title="Unified telco OSS", version="1.0.0")

DEFAULT_ESTATE = "meridian"


def _estate(name: str):
    if name not in ESTATES:
        raise HTTPException(status_code=404, detail=f"unknown estate {name!r}")
    return get_estate(name)


@app.get("/estates")
def estates() -> list[dict[str, Any]]:
    return [
        {
            "estate": name,
            "billing_rules": rule_summary(policy.billing),
            "inventory_rules": {
                "withhold_maintenance_buffer": policy.inventory.withhold_maintenance_buffer,
                "active_circuit_roles": sorted(policy.inventory.active_circuit_roles)
                if policy.inventory.active_circuit_roles
                else "all",
            },
        }
        for name, policy in ESTATES.items()
    ]


@app.get("/billing/invoices")
def invoices(
    estate: str = DEFAULT_ESTATE,
    period: str | None = None,
    account_id: str | None = None,
) -> list[dict[str, Any]]:
    service = _estate(estate)
    return [invoice_dict(i) for i in service.invoices(period=period, account_id=account_id)]


@app.get("/billing/summary")
def billing_summary(estate: str = DEFAULT_ESTATE, period: str | None = None) -> dict[str, Any]:
    service = _estate(estate)
    invoices_ = service.invoices(period=period)
    return {
        "estate": estate,
        "period": period,
        "invoices": len(invoices_),
        "revenue_total": float(service.revenue_total(period=period)),
        "unlinked_usage_records": len(service.unlinked_usage(period=period)),
        "rules": rule_summary(service.policy.billing),
    }


@app.get("/inventory/sites")
def sites(estate: str = DEFAULT_ESTATE, market_id: str | None = None) -> list[dict[str, Any]]:
    return _estate(estate).site_records(market_id=market_id)


@app.get("/inventory/circuits")
def circuits(estate: str = DEFAULT_ESTATE) -> dict[str, Any]:
    return _estate(estate).circuit_summary()


@app.get("/capacity")
def capacity(
    estate: str = DEFAULT_ESTATE,
    requested_mbps: int = Query(0, ge=0),
    market_id: str | None = None,
) -> list[dict[str, Any]]:
    return _estate(estate).capacity(requested_mbps=requested_mbps, market_id=market_id)


@app.get("/network/addressing")
def network_addressing(estate: str = DEFAULT_ESTATE) -> dict[str, Any]:
    return _estate(estate).addressing_summary()


@app.get("/network/orphaned-references")
def orphaned_references(estate: str = DEFAULT_ESTATE) -> dict[str, int]:
    return _estate(estate).orphaned_references()


@app.get("/parity")
def parity(
    period: str = "2026-07", left: str = "meridian", right: str = "vantage"
) -> dict[str, Any]:
    _estate(left)
    _estate(right)
    report = compare(period, left, right)
    return {
        "period": report["period"],
        "left": left,
        "right": right,
        "accounts_compared": report["accounts_compared"],
        "disagreeing_accounts": len(report["differences"]),
        "variance_by_rule": {k: float(v) for k, v in report["variance_by_rule"].items()},
        "variance_by_province": {k: float(v) for k, v in report["variance_by_province"].items()},
        "differences": [
            {
                "billing_ref": row["billing_ref"],
                "province": row["province"],
                f"{left}_total": float(row[f"{left}_total"]),
                f"{right}_total": float(row[f"{right}_total"]),
                "delta": float(row["delta"]),
                "rules": row["rules"],
            }
            for row in report["differences"]
        ],
    }
