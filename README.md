# vantage-net

Inventory, management addressing and billing services for the Vantage network.

One FastAPI service serves the JSON API and HTML dashboards. The Java invoice
reporter and Meridian parity tools run separately. See the
[architecture guide and diagram](docs/architecture.md) for how they fit together.

## Getting started

Use Python 3.10 or newer. From the repository root:

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements.txt
python -m uvicorn app.main:app --reload --port 8000
```

Leave `MONGO_URI` unset to use the checked-in JSON collections in `data/seed/`.
To use MongoDB, set `MONGO_URI` and optionally `MONGO_DB` (default `vantage`).
The selected database must already have the collections; startup does not seed it.

| Local page | Purpose |
| --- | --- |
| [Dashboard](http://localhost:8000/dashboard) | Inventory and billing overview |
| [Invoice register](http://localhost:8000/dashboard/billing) | Filter invoices by period, account ID or billing reference |
| [Capacity check](http://localhost:8000/capacity) | Check sellable bandwidth by location |
| [API docs](http://localhost:8000/docs) | Explore the JSON endpoints |

## Repository layout

| Path | Contents |
| --- | --- |
| [`app/`](app/) | FastAPI entry point, HTTP routers, collection access, and domain rules |
| [`app/network/configs/`](app/network/configs/) | Address plan, routing, firewall, DNS and monitoring files |
| [`data/seed/`](data/seed/) | Local JSON collections for sites, circuits, devices, locations, accounts and usage |
| [`java/vantage-report/`](java/vantage-report/) | Standalone Java 11 invoice reporter |
| [`tools/`](tools/) | Fixture generation and Python–Meridian invoice comparison |
| [`tests/`](tests/) | Python domain and HTTP tests |

## Tests

From the repository root with the virtual environment activated:

```bash
env -u MONGO_URI python -m pytest -q
```

## Java invoice reporter

With JDK 11 and Maven, build and test the reporter and run the resulting JAR
from the repository root:

```bash
mvn -B -f java/vantage-report/pom.xml verify
java -jar java/vantage-report/target/vantage-report-1.6.0.jar 2026-07
```

The CLI uses built-in accounts and defaults to the bundled `usage-sample.csv`.
To use a different CSV, pass its path after the period. Use the header
`account_id,device_uuid,period,usage_mb`. It prints text invoices and a cycle
summary to stdout. The Java reporter has its own billing rules; it does not
run the FastAPI billing engine.

## Meridian fixtures, parity and demo

For these commands, clone [`meridian-telco`](https://github.com/COG-GTM/meridian-telco)
next to this repo (or pass `MERIDIAN_DIR=/path/to/meridian-telco` to `make`). Its Makefile needs a C++
compiler and SQLite development headers to build. Activate the Vantage Python
environment and leave `MONGO_URI` unset to use the same fixture dataset.

To regenerate the shared billing dataset, run `make fixtures` in a clean
workspace. It overwrites Vantage's billing JSON and replaces Meridian's
account and usage fixtures.

```bash
make parity PERIOD=2026-07
make demo
```

`make parity` compares the Python billing engine with Meridian's invoice
binary by `billing_ref`; differences in matched totals yield a nonzero exit
status. It does not start the servers.

`make demo` runs both invoice registers: [Vantage](http://localhost:8000/dashboard/billing)
and [Meridian](http://localhost:8083/billing.html) (Meridian's invoice API uses port 8082).
