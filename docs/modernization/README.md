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
| `phase3-api-templating/` | Async routes, pagination, Jinja2, `/v1` |
| `phase4-java/`         | Java LTS upgrade, virtual threads       |
| `phase5-deploy/`       | Docker, secrets, SBOM, final summary    |

The consolidated reviewer index (per-phase goals, PRs, gates, artifact tables and merge order)
is [`summary.md`](summary.md).

## 1. Boot the app

```bash
python -m venv .venv && .venv/bin/python -m pip install -r requirements.txt -r requirements-dev.txt
.venv/bin/uvicorn app.main:app --port 8000
```

Without a Mongo URI the app serves the JSON fixtures in `data/seed/` (seed mode), which is the
deterministic dataset all recordings should use. Period `2026-07` is the reference billing period
(200 invoices, revenue `1816527.27`).

## 2. Surfaces to record

Record one continuous screen recording visiting, in order:

1. `http://localhost:8000/v1/dashboard`
2. `http://localhost:8000/v1/dashboard/billing` and `…/v1/dashboard/billing?period=2026-07`
3. `http://localhost:8000/v1/capacity` — search a location (e.g. `RIV-01`) and change the requested
   Mbps so the serviceability verdict flips
4. `http://localhost:8000/docs` — expand and execute `GET /v1/billing/invoices?period=2026-07`

Scroll each page to its end so the full content is visible. Also capture API evidence from the
shell:

```bash
curl -s 'http://localhost:8000/v1/billing/invoices?period=2026-07' | python3 -m json.tool > <phase>/pre-billing-invoices.json
curl -s -w '\n%{time_total}s\n' http://localhost:8000/health > <phase>/pre-health.txt
```

Phases that change auth (Phase 1) additionally record an unauthenticated request being rejected
and the `?billing_ref=<script>` payload on `/v1/dashboard/billing`; Phase 2 records `curl` output +
timing proving byte-identical invoices; Phase 4 records the `mvn exec:java` batch run for
`2026-07`.

Phase 5 records the *same* surfaces twice: `pre-*` from the app booted directly with uvicorn
(seed mode) and `post-*` served from the Docker Compose stack (`docker compose up --build`:
Mongo seeded from `data/seed/`), plus terminal captures of the image builds, the seeded compose
boot, the containerised Java batch (`post-java-container-batch.txt`, diff-identical to
`phase4-java/post-output/invoices-2026-07.txt`), the SBOM (`post-sbom.txt` / `post-sbom.json`)
and the image scan (`post-image-scan.txt`).

Legacy paths under `/resources`, `/circuits`, `/billing`, `/network`, `/capacity`, and
`/dashboard` return a 308 redirect to the equivalent `/v1` path. `/health` and `/docs` remain
unversioned.

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
(cd java/vantage-report && mvn -B verify)
```

`make parity` needs the legacy `../meridian-telco` checkout, which was not available in any of the
phase environments; `tests/test_db.py::test_billing_invoices_match_phase0_baseline`,
`tests/test_security.py::test_billing_ops_invoice_response_matches_baseline` and `tests/test_api.py::test_invoice_pagination_matches_phase0_baseline`
compare the live invoice output with `phase0-baseline/pre-billing-invoices.json` instead.

## 5. Secrets

Deployment configuration never passes secrets as raw environment variables. `app/settings.py`
resolves each setting `NAME` as `<NAME>_FILE` (path to a mounted secret file, e.g.
`/run/secrets/mongo_uri`) first, then the plain `NAME` variable (local development only), then
`None`. `docker-compose.yml` declares `mongo_uri`, `mongo_db` and `vantage_auth_dev_secret` as
top-level file-based `secrets:` (sources in `deploy/secrets/`, only `*.example` committed) and
sets `MONGO_URI_FILE`, `MONGO_DB_FILE`, `VANTAGE_AUTH_DEV_SECRET_FILE` on the `app` service. A
vault (HashiCorp Vault Agent templates, AWS Secrets Manager via the Secrets Store CSI driver or an
init container, Kubernetes `Secret` volumes) is wired by rendering the value into the same mounted
file path — the application code does not change. See the README "Secrets" section for the
resolution table.

## 6. Supply chain

`.github/workflows/supply-chain.yml` builds the Python and Java images, generates SPDX SBOMs with
`anchore/sbom-action` (repository + both images, uploaded as workflow artifacts) and scans both
images with `aquasecurity/trivy-action` (`ignore-unfixed`, fails on CRITICAL/HIGH, SARIF uploaded
to the Security tab). Accepted findings are recorded with a justification in `.trivyignore`.
