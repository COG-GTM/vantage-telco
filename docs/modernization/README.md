# Modernization program — pre/post capture procedure

Every modernization phase ships with visual evidence of the surfaces it touches, captured
**before** and **after** the change, so a human reviewer can compare them without running the
code. Artifacts live under `docs/modernization/<phase>/` and are named `pre.*` / `post.*`
(or `pre-<surface>.*` / `post-<surface>.*` when a phase touches several surfaces).

| Phase directory        | Scope                                  |
| ---------------------- | -------------------------------------- |
| `phase0-baseline/`     | Current state before any change         |
| `phase1-security/`     | Auth, PII redaction, XSS, headers       |
| `phase2-data-layer/`   | Mongo client lifecycle, query pushdown  |
| `phase3-api/`          | Async routes, pagination, Jinja2, `/v1` |
| `phase4-java/`         | Java LTS upgrade, virtual threads       |
| `phase5-deploy/`       | Docker, secrets, SBOM, final summary    |

## 1. Boot the app

```bash
python -m venv .venv && .venv/bin/python -m pip install -r requirements.txt -r requirements-dev.txt
.venv/bin/uvicorn app.main:app --port 8000
```

Without `MONGO_URI` the app serves the JSON fixtures in `data/seed/` (seed mode), which is the
deterministic dataset all recordings should use. Period `2026-07` is the reference billing period
(200 invoices, revenue `1816527.27`).

## 2. Surfaces to record

Record one continuous screen recording visiting, in order:

1. `http://localhost:8000/dashboard`
2. `http://localhost:8000/dashboard/billing` and `…/dashboard/billing?period=2026-07`
3. `http://localhost:8000/capacity` — search a location (e.g. `RIV-01`) and change the requested
   Mbps so the serviceability verdict flips
4. `http://localhost:8000/docs` — expand and execute `GET /billing/invoices?period=2026-07`

Scroll each page to its end so the full content is visible. Also capture API evidence from the
shell:

```bash
curl -s 'http://localhost:8000/billing/invoices?period=2026-07' | python3 -m json.tool > <phase>/pre-billing-invoices.json
curl -s -w '\n%{time_total}s\n' http://localhost:8000/health > <phase>/pre-health.txt
```

Phases that change auth (Phase 1) additionally record an unauthenticated request being rejected
and the `?billing_ref=<script>` payload on `/dashboard/billing`; Phase 2 records `curl` output +
timing proving byte-identical invoices; Phase 4 records the `mvn exec:java` batch run for
`2026-07`.

## 3. Where to save

```
docs/modernization/<phase>/
  pre-recording.mp4            post-recording.mp4
  pre-dashboard.png            post-dashboard.png
  pre-dashboard-billing.png    post-dashboard-billing.png
  pre-capacity.png             post-capacity.png
  pre-swagger.png              post-swagger.png
  pre-billing-invoices.json    post-billing-invoices.json
  pre-health.txt               post-health.txt
```

Take the `pre.*` set on `main` before applying the phase's change, and the `post.*` set on the
phase branch after the change. Commit both in the phase's PR and link them from the PR
description. `diff pre-billing-invoices.json post-billing-invoices.json` must be empty for every
phase that does not intentionally change billing output.

## 4. Quality gates every phase must keep green

```bash
make test lint typecheck coverage audit PY=.venv/bin/python
make parity PY=.venv/bin/python   # requires ../meridian-telco checkout; must exit 0
```
