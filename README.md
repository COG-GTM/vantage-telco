# vantage-net

Inventory, management addressing and billing services for the Vantage network.

Vantage runs a single FastAPI application backed by MongoDB. For local
development and CI the same collections are read from `data/seed`, so the app
and the test suite run with no database.

## Getting started

```bash
git submodule update --init          # third_party/telco-rules
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt      # builds the telco-rules binding (needs g++)
uvicorn app.main:app --reload --port 8000
```

Point the app at a real database by exporting `MONGO_URI` (and optionally
`MONGO_DB`, default `vantage`).

## Shared business rules

Billing, capacity, circuit roll-up, lifecycle and addressing rules come from
[`telco-rules`](https://github.com/COG-GTM/telco-rules), vendored as a git
submodule in `third_party/telco-rules`. meridian-telco uses the same library, so
the two estates rate and roll up identically. Where vantage used to differ from
meridian, the rule chosen and the reason are in
`third_party/telco-rules/DECISIONS.md`. Change rules there, not here.

## Modules

### `app/inventory`

Network resources keyed by `device_uuid`, grouped by `market_id` (fine-grained
metro codes), with a five-state `lifecycle_state`: `ACTIVE`, `MAINTENANCE`,
`RETIRED`, `PLANNED`, `RESERVED`.

- `capacity.py` — `available = total - allocated` (telco-rules D-07). The
  `maintenance_buffer_mbps` on each record is reported but not withheld.
- `circuits.py` — every circuit in an active lifecycle state counts, whatever its
  role, so standby and failover circuits count (D-08).

Endpoints: `GET /resources`, `GET /resources/{device_uuid}`, `GET /circuits`.

### `app/network`

Management addressing. Every device holds an address out of the
`10.20.0.0/16` management supernet. `10.20.250.0/24` (planned aggregation
build-out, still exposed as `growth_pool`) and `10.20.251.0/24` (lab) are
reserved ranges (D-10).
Generated artifacts under `app/network/configs` reference those addresses:

| Path | Format | Purpose |
| --- | --- | --- |
| `configs/routing/*.yaml` | YAML | per-market static routes |
| `configs/firewall/*.yaml` | YAML | management-plane ACLs |
| `configs/dns/*.zone` | zone file | forward records for management names |
| `configs/monitoring/*.json` | JSON | NOC poller targets |
| `configs/address_plan.json` | JSON | supernet, growth pool, external-BGP devices |

`addressing.py` can list every config file referencing a given address and
detect references to addresses no device owns.

Endpoints: `GET /network/addressing`, `GET /network/devices`,
`GET /network/references?address=...`.

Devices flagged `external_bgp` are customer-facing and must not be renumbered.

### `app/billing`

Each module is a thin wrapper over telco-rules:

- `rating.py` — whole gigabytes, partial gigabytes round up, $10/GB overage (D-01).
  `overage_mb` is still reported for information.
- `proration.py` — 30-day billing month for mid-cycle plan changes (D-05).
- `promo.py` — promo credits expire at the end of the cycle they were issued in (D-02).
- `suspension.py` — a suspended line is billed in full, no credit (D-04).
- `lines.py` — 3-9 lines 5% off recurring, 10 or more 10%.
- `latefee.py` — 10 days grace after the due date, then 1.5% of the balance.
- `tax.py` — GST/HST on the pre-discount subtotal, PST/QST after the loyalty
  discount (D-03).
- `discounts.py` — the loyalty credit comes off the subtotal.
- `invoices.py` — invoice construction via `telco_rules.compute_invoice`, plus
  `unlinked_usage()` for usage that was mediated without a billing account.

Each charge line is rounded to cents, then the total is rounded (D-06). Provinces
billed: BC, AB, ON, QC.

Endpoints: `GET /billing/invoices`, `GET /billing/usage-summary`. The invoice
register page is `GET /dashboard/billing` (filter by `period`, `account_id` or
`billing_ref`); it shows the province and the tax lines per invoice.

## Capacity check (sales engineering)

`GET /capacity` is the sales-facing page: enter the bandwidth being quoted and
it shows, per customer location, what is actually sellable. Availability comes
from telco-rules via `app/inventory/capacity.py`. No maintenance buffer is
withheld (D-07):

```
available = total_capacity - allocated
```

Serviceable locations live in `data/seed/locations.json`. The same figures are
available as JSON from `GET /capacity/locations?requested_mbps=...` and
`GET /capacity/locations/{location_code}`.

## Dashboard

`GET /dashboard` renders the current inventory and billing figures as a plain
HTML page.

## Tests

```bash
pytest
```

`tests/` covers capacity, circuit roll-ups, rating and discount ordering,
addressing/reference integrity, and the HTTP surface.

## `java/vantage-report`

The archived invoice artifacts the NOC keeps per cycle are rendered by a
separate Maven module in `java/vantage-report`, built and run on Java 11. It
re-implements the rating rules in `app/billing` (exact-MB overage, tax on the
pre-discount subtotal, loyalty credit applied post-tax) and renders each
invoice as plain text plus a per-charge CSV. It has **not** been moved onto
telco-rules yet, so its output still follows the old vantage rules
(DECISIONS.md D-13).

```bash
cd java/vantage-report
mvn -B verify
mvn -q exec:java -Dexec.mainClass=net.vantage.report.Main -Dexec.args="2026-07"
```

Usage comes from the mediation CSV export
(`account_id,device_uuid,period,usage_mb`); with no path argument the bundled
`usage-sample.csv` is used. Invoices are rendered concurrently by
`pipeline/BatchRunner` over a fixed platform-thread pool.

## Seed data

`data/seed/` holds `sites.json` (97), `circuits.json`, `devices.json`,
`accounts.json` (200 billing accounts across BC/AB/ON/QC), `usage.json` and
`locations.json`.

The billing fixtures are generated, not hand-edited. `tools/fixtures` writes
both estates' copies of the same customer book from one seed, so an account is
the same customer on both sides and joins on `billing_ref`:

```bash
make fixtures MERIDIAN_DIR=../meridian-telco
```

## Invoice parity with meridian-telco

`tools/parity` runs the legacy meridian-telco register and this service over the
same usage feed, joins on `billing_ref` and prints every account whose invoice
total disagrees, with the rules implicated and the variance by rule and by
province.

```bash
make parity PERIOD=2026-07 MERIDIAN_DIR=../meridian-telco
```

It exits non-zero while the two estates disagree, and it also compares each
invoice line both registers carry. Since both estates moved to telco-rules it
reports `differing=0`.

## Demo

```bash
make demo MERIDIAN_DIR=../meridian-telco
```

Brings up both invoice registers side by side: vantage on
<http://localhost:8000/dashboard/billing> and meridian on
<http://localhost:8083/billing.html> (its invoice API on :8082).
