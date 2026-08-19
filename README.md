# vantage-net

Inventory, management addressing and billing services for the Vantage network.

Vantage runs a single FastAPI application backed by MongoDB. For local
development and CI the same collections are read from `data/seed`, so the app
and the test suite run with no database.

## Getting started

```bash
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
uvicorn app.main:app --reload --port 8000
```

Point the app at a real database by exporting `MONGO_URI` (and optionally
`MONGO_DB`, default `vantage`).

## Modules

### `app/inventory`

Network resources keyed by `device_uuid`, grouped by `market_id` (fine-grained
metro codes), with a five-state `lifecycle_state`: `ACTIVE`, `MAINTENANCE`,
`RETIRED`, `PLANNED`, `RESERVED`.

- `capacity.py` — `available = total - allocated - maintenance_buffer`. A link
  reserved for maintenance is not spare capacity.
- `circuits.py` — standby and failover circuits are excluded from active counts
  and active capacity.

Endpoints: `GET /resources`, `GET /resources/{device_uuid}`, `GET /circuits`.

### `app/network`

Management addressing. Every device holds an address out of the
`10.20.0.0/16` management supernet; `10.20.250.0/24` is the growth pool.
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

The rules themselves are not implemented here. They live in the shared library
[COG-GTM/telco-billing-rules](https://github.com/COG-GTM/telco-billing-rules),
vendored into `vendor/` and used by the meridian estate too, so the two
registers cannot drift apart again:

- usage rated in whole gigabytes, partial gigabytes rounding up, $10/GB overage.
- mid-cycle plan changes split on a fixed 30-day billing month.
- promo credits live only in the cycle they were issued in.
- a suspended line is billed the full month, no credit.
- 3-9 lines 5% off recurring, 10 or more 10%.
- 10 days grace after the due date, then 1.5% of the balance.
- GST/HST on the pre-discount subtotal, PST/QST on the post-loyalty amount.
- every charge line rounded half-up to cents as it is produced.

Provinces billed: BC, AB, ON, QC.

This package holds the wiring only:

- `rules.py` — the shared rules, re-exported. Import billing rules from here.
- `invoices.py` — invoice construction, plus `unlinked_usage()` for usage that
  was mediated without a billing account.

Do not edit anything under `vendor/`. Change the rule upstream, then re-vendor:

```bash
python tools/vendor.py --python ../vantage-telco/vendor   # from the library repo
```

`make test` runs the shared conformance vectors and `vendor/vendor_check.py`,
which fails if the vendored copy was patched in place.

Endpoints: `GET /billing/invoices`, `GET /billing/usage-summary`. The invoice
register page is `GET /dashboard/billing` (filter by `period`, `account_id` or
`billing_ref`); it shows the province and the tax lines per invoice.

## Capacity check (sales engineering)

`GET /capacity` is the sales-facing page: enter the bandwidth being quoted and
it shows, per customer location, what is actually sellable. Availability comes
from `app/inventory/capacity.py`, so the maintenance buffer is withheld:

```
available = total_capacity - allocated - maintenance_buffer
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
re-implements a third set of rating rules of its own (exact-MB overage, one flat
tax percentage, loyalty credit applied post-tax, no proration, promo, suspension
or late fee) and renders each invoice as plain text plus a per-charge CSV. It
does **not** go through the shared rules library, so its figures do not
reconcile with the invoice register; treat the register as authoritative until
the reporter is moved onto the library.

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

It exits non-zero while the two estates still disagree.

## Demo

```bash
make demo MERIDIAN_DIR=../meridian-telco
```

Brings up both invoice registers side by side: vantage on
<http://localhost:8000/dashboard/billing> and meridian on
<http://localhost:8083/billing.html> (its invoice API on :8082).
