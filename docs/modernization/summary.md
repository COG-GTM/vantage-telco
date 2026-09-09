# Modernization summary — reviewer index

Six phases modernised `vantage-telco` (FastAPI + MongoDB telecom API, Java batch renderer)
without changing billing output: the `invoices` array for `GET /v1/billing/invoices?period=2026-07`
is byte-identical to [`phase0-baseline/pre-billing-invoices.json`](phase0-baseline/pre-billing-invoices.json)
in every phase (200 invoices, revenue `$1,816,527.27`, 22 capacity locations).

## Merge order

Every phase PR is based on the branch before it, so merge bottom-up:

1. [#26](https://github.com/COG-GTM/vantage-telco/pull/26) Phase 0 tooling → `main`
2. [#29](https://github.com/COG-GTM/vantage-telco/pull/29) Phase 1 security and
   [#28](https://github.com/COG-GTM/vantage-telco/pull/28) Phase 2 data layer (both based on Phase 0),
   merged together on `devin/1788937178-phase12-integration`
3. [#30](https://github.com/COG-GTM/vantage-telco/pull/30) Phase 3 API/templating (based on the Phase 1+2 integration branch)
4. [#27](https://github.com/COG-GTM/vantage-telco/pull/27) Phase 4 Java 21 (based on Phase 0; merged with Phase 3 on
   `devin/1788938278-phase34-integration`, commit `feature: merge phase 3 and phase 4 for phase 5 base`)
5. [#PHASE5_PR](PHASE5_PR_URL) Phase 5 deploy + supply chain (based on the Phase 3+4 integration branch)

Merging `#26 → #29 → #28 → #30 → #27 → Phase 5` in that order (or merging the Phase 5 PR after its
integration base) yields the same tree as the Phase 5 branch.

## Known caveat — external parity

`make parity` (`tools/parity`, compares against the legacy `../meridian-telco` checkout) could not be
run in any phase environment because the sibling checkout was absent. Parity is instead asserted
by tests that compare live output with the Phase 0 baseline:
`tests/test_db.py::test_billing_invoices_match_phase0_baseline`,
`tests/test_security.py::test_billing_ops_invoice_response_matches_baseline`,
`tests/test_api.py::test_invoice_pagination_matches_phase0_baseline`, plus per-phase
`diff pre-billing-invoices.json post-billing-invoices.json` (empty everywhere; the Phase 5 post capture
is served from MongoDB and is identical in raw order).

---

## Phase 0 — Baseline and tooling

- **Goal:** lock in the current behaviour and add quality gates before any change.
- **PR:** [#26](https://github.com/COG-GTM/vantage-telco/pull/26) · **Branch:** `devin/1788934482-phase0-tooling`
- **Key changes**
  - `ruff`, `mypy`, `pip-audit`, `pytest-cov` as dev dependencies; Makefile targets `lint`, `typecheck`, `audit`, `coverage` (`COV_MIN=85`).
  - Pinned `requirements.txt` + `requirements.lock`.
  - CI `tests.yml` runs lint / typecheck / coverage / audit.
  - `docs/modernization/README.md` capture procedure and the Phase 0 baseline evidence.
- **Gates:** 48 tests passed, ruff/mypy clean, coverage 86.14%, pip-audit clean.

| Artifact | Pre |
| --- | --- |
| Recording | [pre-recording.mp4](phase0-baseline/pre-recording.mp4) |
| Dashboard | [pre-dashboard.png](phase0-baseline/pre-dashboard.png) |
| Billing dashboard | [pre-dashboard-billing.png](phase0-baseline/pre-dashboard-billing.png) |
| Capacity | [pre-capacity.png](phase0-baseline/pre-capacity.png) |
| Swagger | [pre-swagger.png](phase0-baseline/pre-swagger.png) |
| Invoices JSON | [pre-billing-invoices.json](phase0-baseline/pre-billing-invoices.json) |
| Health | [pre-health.txt](phase0-baseline/pre-health.txt) |

## Phase 1 — Security

- **Goal:** authenticate and authorise every business route, redact PII, harden HTML output.
- **PR:** [#29](https://github.com/COG-GTM/vantage-telco/pull/29) · **Branch:** `devin/1788935732-phase1-security`
- **Key changes**
  - `app/security.py`: HMAC bearer tokens with scopes `sales-engineering`, `noc`, `billing-ops`; CLI to mint dev tokens.
  - Security middleware: 401/403 per router, security headers, CORS allow-list, per-IP rate limit.
  - Invoice PII redacted for `noc`, visible for `billing-ops`.
  - XSS: dashboard query parameters escaped (`?billing_ref=<script>` evidence).
  - `/health`, `/docs`, `/openapi.json` intentionally unauthenticated.
- **Gates:** 88 tests passed, ruff/mypy clean, coverage 88.29%, pip-audit clean.

| Artifact | Pre | Post |
| --- | --- | --- |
| Recording | [pre-recording.mp4](phase1-security/pre-recording.mp4) | [post-recording.mp4](phase1-security/post-recording.mp4) |
| Dashboard | [pre-dashboard.png](phase1-security/pre-dashboard.png) | [post-dashboard.png](phase1-security/post-dashboard.png) |
| Billing dashboard | [pre-dashboard-billing.png](phase1-security/pre-dashboard-billing.png) | [post-dashboard-billing.png](phase1-security/post-dashboard-billing.png) |
| Capacity | [pre-capacity.png](phase1-security/pre-capacity.png) | [post-capacity.png](phase1-security/post-capacity.png) |
| Swagger | [pre-swagger.png](phase1-security/pre-swagger.png) | [post-swagger.png](phase1-security/post-swagger.png) |
| Invoices JSON | [pre-billing-invoices.json](phase1-security/pre-billing-invoices.json) | [post-billing-invoices.json](phase1-security/post-billing-invoices.json) |
| Health | [pre-health.txt](phase1-security/pre-health.txt) | [post-health.txt](phase1-security/post-health.txt) |
| Auth curl | [pre-curl-auth.txt](phase1-security/pre-curl-auth.txt) | [post-curl-auth.txt](phase1-security/post-curl-auth.txt) |
| XSS page | [pre-xss.png](phase1-security/pre-xss.png) | [post-xss.png](phase1-security/post-xss.png) |
| XSS breakout | [pre-xss-breakout.png](phase1-security/pre-xss-breakout.png) | [post-xss-breakout.png](phase1-security/post-xss-breakout.png) |
| XSS dialogs | [pre-xss-dialogs.txt](phase1-security/pre-xss-dialogs.txt) | [post-xss-dialogs.txt](phase1-security/post-xss-dialogs.txt) |

## Phase 2 — Data layer

- **Goal:** one pooled Mongo client, query pushdown, indexes, no per-request connections.
- **PR:** [#28](https://github.com/COG-GTM/vantage-telco/pull/28) · **Branch:** `devin/1788935714-phase2-data-layer`
- **Key changes**
  - Shared `mongo_client()` created once, closed in the FastAPI lifespan.
  - `find_documents()` / `all_documents()` pushing filters to Mongo, with identical semantics in seed mode (`$in`, `None`, missing keys).
  - `ensure_indexes()` at startup.
  - `mongomock`-based tests and the Phase 0 invoice-baseline test.
- **Gates:** tests passed, ruff/mypy clean, coverage 88.89%, pip-audit clean.

| Artifact | Pre | Post |
| --- | --- | --- |
| Recording | [pre-recording.mp4](phase2-data-layer/pre-recording.mp4) | [post-recording.mp4](phase2-data-layer/post-recording.mp4) |
| Dashboard | [pre-dashboard.png](phase2-data-layer/pre-dashboard.png) | [post-dashboard.png](phase2-data-layer/post-dashboard.png) |
| Billing dashboard | [pre-dashboard-billing.png](phase2-data-layer/pre-dashboard-billing.png) | [post-dashboard-billing.png](phase2-data-layer/post-dashboard-billing.png) |
| Capacity | [pre-capacity.png](phase2-data-layer/pre-capacity.png) | [post-capacity.png](phase2-data-layer/post-capacity.png) |
| Swagger | [pre-swagger.png](phase2-data-layer/pre-swagger.png) | [post-swagger.png](phase2-data-layer/post-swagger.png) |
| Invoices JSON | [pre-billing-invoices.json](phase2-data-layer/pre-billing-invoices.json) | [post-billing-invoices.json](phase2-data-layer/post-billing-invoices.json) |
| Health | [pre-health.txt](phase2-data-layer/pre-health.txt) | [post-health.txt](phase2-data-layer/post-health.txt) |
| curl timing | [pre-curl-timing.txt](phase2-data-layer/pre-curl-timing.txt) | [post-curl-timing.txt](phase2-data-layer/post-curl-timing.txt) |
| curl diff terminal | — | [post-curl-diff-terminal.png](phase2-data-layer/post-curl-diff-terminal.png) |

## Phase 3 — API and templating

- **Goal:** async handlers, versioned API, pagination, templates instead of inline HTML.
- **PR:** [#30](https://github.com/COG-GTM/vantage-telco/pull/30) · **Branch:** `devin/1788937252-phase3-api-templating`
- **Key changes**
  - All routes under `/v1`; legacy paths return `308` redirects; `/health` and `/docs` unversioned.
  - Async handlers; list endpoints paginated (`limit`/`offset`, default 50) with aggregates over the full set.
  - Jinja2 templates (`app/templates/`, autoescape) replacing inline HTML.
  - App version `3.0.0`.
- **Gates:** 106 tests passed, ruff/mypy clean (35 files), coverage 90.69%, pip-audit clean.

| Artifact | Pre | Post |
| --- | --- | --- |
| Recording | [pre-recording.mp4](phase3-api-templating/pre-recording.mp4) | [post-recording.mp4](phase3-api-templating/post-recording.mp4) |
| Dashboard | [pre-dashboard.png](phase3-api-templating/pre-dashboard.png) | [post-dashboard.png](phase3-api-templating/post-dashboard.png) |
| Billing dashboard | [pre-dashboard-billing.png](phase3-api-templating/pre-dashboard-billing.png) | [post-dashboard-billing.png](phase3-api-templating/post-dashboard-billing.png) |
| Capacity | [pre-capacity.png](phase3-api-templating/pre-capacity.png) | [post-capacity.png](phase3-api-templating/post-capacity.png) |
| Swagger | [pre-swagger.png](phase3-api-templating/pre-swagger.png) | [post-swagger.png](phase3-api-templating/post-swagger.png) |
| Invoices JSON | [pre-billing-invoices.json](phase3-api-templating/pre-billing-invoices.json) | [post-billing-invoices.json](phase3-api-templating/post-billing-invoices.json) |
| Health | [pre-health.txt](phase3-api-templating/pre-health.txt) | [post-health.txt](phase3-api-templating/post-health.txt) |
| Auth curl | [pre-curl-auth.txt](phase3-api-templating/pre-curl-auth.txt) | [post-curl-auth.txt](phase3-api-templating/post-curl-auth.txt) |
| Pagination curl | [pre-curl-pagination.txt](phase3-api-templating/pre-curl-pagination.txt) | [post-curl-pagination.txt](phase3-api-templating/post-curl-pagination.txt) |
| Redirect curl | — | [post-curl-redirect.txt](phase3-api-templating/post-curl-redirect.txt) |
| XSS page | [pre-xss.png](phase3-api-templating/pre-xss.png) | [post-xss.png](phase3-api-templating/post-xss.png) |
| XSS breakout | [pre-xss-breakout.png](phase3-api-templating/pre-xss-breakout.png) | [post-xss-breakout.png](phase3-api-templating/post-xss-breakout.png) |
| XSS dialogs | [pre-xss-dialogs.txt](phase3-api-templating/pre-xss-dialogs.txt) | [post-xss-dialogs.txt](phase3-api-templating/post-xss-dialogs.txt) |

## Phase 4 — Java 21 batch renderer

- **Goal:** move `java/vantage-report` to Java 21 LTS and virtual threads, byte-identical output.
- **PR:** [#27](https://github.com/COG-GTM/vantage-telco/pull/27) · **Branch:** `devin/1788935692-phase4-java21`
- **Key changes**
  - `maven.compiler.release` 21; plugin versions pinned.
  - `BatchRunner` renders invoices on virtual threads (`vantage-render-*`), order preserved, executor closed on `close()`.
  - `BatchRunnerTest` (7 tests) — 28 tests total.
  - `.github/workflows/java.yml` runs `mvn -B verify` on Temurin 21.
- **Gates:** `mvn -B verify` 28 tests, 0 failures; `invoices-2026-07.txt` identical pre/post.

| Artifact | Pre | Post |
| --- | --- | --- |
| Recording | [pre-recording.mp4](phase4-java/pre-recording.mp4) | [post-recording.mp4](phase4-java/post-recording.mp4) |
| Batch terminal | [pre-batch.txt](phase4-java/pre-batch.txt) | [post-batch.txt](phase4-java/post-batch.txt) |
| Invoice output | [pre-output/invoices-2026-07.txt](phase4-java/pre-output/invoices-2026-07.txt) | [post-output/invoices-2026-07.txt](phase4-java/post-output/invoices-2026-07.txt) |

## Phase 5 — Deploy and supply chain

- **Goal:** containerise both applications, file-based secrets, SBOM + vulnerability gates.
- **PR:** [#PHASE5_PR](PHASE5_PR_URL) · **Branch:** `devin/1788938421-phase5-deploy` (base `devin/1788938278-phase34-integration`)
- **Key changes**
  - `Dockerfile` (python:3.12-slim, multi-stage, non-root, pip removed from the runtime, `HEALTHCHECK /health`) and `java/vantage-report/Dockerfile` (Maven 21 build → Temurin 21 JRE Alpine, non-root, `/out` volume).
  - `docker-compose.yml`: `mongo:7` + one-shot `mongo-seed` (`mongoimport --jsonArray` of `data/seed/*.json`) + `app` + `report` (profile `batch`); top-level file `secrets:`.
  - `app/settings.py::get_setting` — `<NAME>_FILE` → env → `None`; `app/db.py` and `app/security.py` switched to it; Mongo `_id` projected out of API responses.
  - `.github/workflows/supply-chain.yml`: SBOMs (`anchore/sbom-action`, SPDX JSON) for repo + both images, Trivy CRITICAL/HIGH gate with `ignore-unfixed`, SARIF upload.
  - README / modernization README: Compose, Secrets (`_FILE`, vault wiring), Supply chain sections.
- **Gates:** see [final-gates.txt](phase5-deploy/final-gates.txt) — 117 tests passed, ruff/mypy clean, coverage 90.96%, pip-audit clean, `mvn -B verify` 28 tests; both images scan clean (0 CRITICAL / 0 HIGH).

| Artifact | Pre (uvicorn, seed mode) | Post (Docker Compose, MongoDB) |
| --- | --- | --- |
| Recording | [pre-recording.mp4](phase5-deploy/pre-recording.mp4) | [post-recording.mp4](phase5-deploy/post-recording.mp4) |
| Dashboard | [pre-dashboard.png](phase5-deploy/pre-dashboard.png) | [post-dashboard.png](phase5-deploy/post-dashboard.png) |
| Billing dashboard | [pre-dashboard-billing.png](phase5-deploy/pre-dashboard-billing.png) | [post-dashboard-billing.png](phase5-deploy/post-dashboard-billing.png) |
| Capacity | [pre-capacity.png](phase5-deploy/pre-capacity.png) | [post-capacity.png](phase5-deploy/post-capacity.png) |
| Swagger | [pre-swagger.png](phase5-deploy/pre-swagger.png) | [post-swagger.png](phase5-deploy/post-swagger.png) |
| Invoices JSON (all 200) | [pre-billing-invoices.json](phase5-deploy/pre-billing-invoices.json) | [post-billing-invoices.json](phase5-deploy/post-billing-invoices.json) |
| Health | [pre-health.txt](phase5-deploy/pre-health.txt) | [post-health.txt](phase5-deploy/post-health.txt) |
| Health curl | [pre-curl-health.txt](phase5-deploy/pre-curl-health.txt) | [post-curl-health.txt](phase5-deploy/post-curl-health.txt) |
| Auth curl | [pre-curl-auth.txt](phase5-deploy/pre-curl-auth.txt) | [post-curl-auth.txt](phase5-deploy/post-curl-auth.txt) |
| Pagination curl | [pre-curl-pagination.txt](phase5-deploy/pre-curl-pagination.txt) | [post-curl-pagination.txt](phase5-deploy/post-curl-pagination.txt) |
| XSS page / breakout / dialogs | [pre-xss.png](phase5-deploy/pre-xss.png) · [pre-xss-breakout.png](phase5-deploy/pre-xss-breakout.png) · [pre-xss-dialogs.txt](phase5-deploy/pre-xss-dialogs.txt) | [post-xss.png](phase5-deploy/post-xss.png) · [post-xss-breakout.png](phase5-deploy/post-xss-breakout.png) · [post-xss-dialogs.txt](phase5-deploy/post-xss-dialogs.txt) |
| API checks (no `_id` leakage) | — | [post-api-checks.txt](phase5-deploy/post-api-checks.txt) |
| Capture log | — | [post-capture.txt](phase5-deploy/post-capture.txt) |
| Python image build | — | [post-docker-build.txt](phase5-deploy/post-docker-build.txt) |
| Compose up (seed counts) | — | [post-compose-up.txt](phase5-deploy/post-compose-up.txt) |
| Java image build | — | [post-java-image-build.txt](phase5-deploy/post-java-image-build.txt) |
| Java container batch | — | [post-java-container-batch.txt](phase5-deploy/post-java-container-batch.txt) · [post-java-output/invoices-2026-07.txt](phase5-deploy/post-java-output/invoices-2026-07.txt) |
| SBOM | — | [post-sbom.txt](phase5-deploy/post-sbom.txt) · [post-sbom.json](phase5-deploy/post-sbom.json) |
| Image scan | — | [post-image-scan.txt](phase5-deploy/post-image-scan.txt) |
| Final gates | — | [final-gates.txt](phase5-deploy/final-gates.txt) |
