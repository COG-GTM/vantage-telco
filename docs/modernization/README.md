# Modernization program — review artifacts

Every modernization phase lands with a **before** and **after** capture of the
surfaces it touches so a human reviewer can compare them without running the
code. Artifacts live under `docs/modernization/<phase>/` and are named
`pre-*` / `post-*`.

| Phase | Directory | Scope |
| --- | --- | --- |
| 0 | `phase0-baseline/` | Tooling + CI; baseline of the current app (`pre-*` only) |
| 1 | `phase1-security/` | OAuth2, PII gating, XSS escaping, security headers |
| 2 | `phase2-data-layer/` | Mongo client lifecycle, query push-down, invoice N+1 |
| 3 | `phase3-api/` | async handlers, pagination, Jinja2 templates, `/v1` |
| 4 | `phase4-java21/` | Java 21 + virtual threads in `java/vantage-report` |
| 5 | `phase5-deploy/` | Docker, secrets, SBOM, final validation + `summary.md` |

## Surfaces to capture

1. `GET /dashboard` — inventory + billing tiles (NOC).
2. `GET /dashboard/billing?period=2026-07` — invoice register (billing ops).
3. `GET /capacity` — sales-engineering capacity check, with a bandwidth and a
   location search entered.
4. API endpoints — `/health`, `/resources`, `/circuits`, `/network/addressing`,
   `/billing/invoices`, `/capacity/locations` via `curl` (or the Swagger UI at
   `/docs` when a phase changes request/response shape).

## Procedure

```bash
# 1. Boot the app (seed-file mode, no Mongo needed)
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt -r requirements-dev.txt
pip install playwright && playwright install chromium
uvicorn app.main:app --port 8000 &

# 2. BEFORE your change, on the base commit:
python docs/modernization/capture.py docs/modernization/<phase> pre

# 3. Apply the change, restart uvicorn, then:
python docs/modernization/capture.py docs/modernization/<phase> post
```

`capture.py` writes, per prefix:

| File | Content |
| --- | --- |
| `<prefix>-dashboard.png` | full-page screenshot of `/dashboard` |
| `<prefix>-dashboard-billing.png` | full-page screenshot of `/dashboard/billing?period=2026-07` |
| `<prefix>-capacity.png` | `/capacity` after quoting 500 Mbps and searching "Riverside" |
| `<prefix>-walkthrough.webm` | one headless-browser video visiting all three pages |
| `<prefix>-api.txt` | `curl` dumps (status + JSON) of the API endpoints listed above |

Captures are headless (no browser chrome, cursor or scrollbars). If a phase
needs an extra surface (e.g. an XSS payload URL, an unauthenticated request
being rejected, `mvn exec:java` output), add it alongside with the same
`pre-`/`post-` naming and mention it in the phase's PR description.

## Rules

- Never regenerate a `pre-*` artifact after your change has landed; it must
  reflect the base commit.
- `post-*` must be produced from the exact commit in the PR.
- Commit the artifacts with the PR that produced them.
- Billing parity (`tools/parity`) must exit zero before and after.
