# Modernization review summary

This index collects the implementation scope, review artifacts, and merge
order for the Vantage modernization program.

## Phases

### Phase 0 — tooling and capture harness

[PR #20](https://github.com/COG-GTM/vantage-telco/pull/20) established pinned
runtime and development dependencies, Makefile lint/typecheck/coverage/audit
gates, CI, and the Playwright-based before/after capture harness. It also
captured the baseline application surfaces without changing application
behavior.

Artifacts: [pre-api.txt](phase0-baseline/pre-api.txt),
[pre-capacity.png](phase0-baseline/pre-capacity.png),
[pre-dashboard-billing.png](phase0-baseline/pre-dashboard-billing.png),
[pre-dashboard.png](phase0-baseline/pre-dashboard.png),
[pre-walkthrough.webm](phase0-baseline/pre-walkthrough.webm).

### Phase 1 — security

[PR #23](https://github.com/COG-GTM/vantage-telco/pull/23) added OAuth2/OIDC
bearer authentication, scope-based router authorization, billing PII
redaction for NOC callers, reflected-XSS escaping, security headers, CORS,
and rate limiting. The phase kept `/health` open, added local HS256
development-token support, and recorded authenticated and unauthenticated
security behavior.

Artifacts: [pre-api.txt](phase1-security/pre-api.txt),
[post-api.txt](phase1-security/post-api.txt),
[pre-auth.txt](phase1-security/pre-auth.txt),
[post-auth.txt](phase1-security/post-auth.txt),
[pre-capacity.png](phase1-security/pre-capacity.png),
[post-capacity.png](phase1-security/post-capacity.png),
[pre-dashboard-billing.png](phase1-security/pre-dashboard-billing.png),
[post-dashboard-billing.png](phase1-security/post-dashboard-billing.png),
[post-dashboard-billing-noc-redacted.png](phase1-security/post-dashboard-billing-noc-redacted.png),
[pre-dashboard.png](phase1-security/pre-dashboard.png),
[post-dashboard.png](phase1-security/post-dashboard.png),
[pre-walkthrough.webm](phase1-security/pre-walkthrough.webm),
[post-walkthrough.webm](phase1-security/post-walkthrough.webm),
[pre-xss.html](phase1-security/pre-xss.html),
[post-xss.html](phase1-security/post-xss.html),
[pre-xss.png](phase1-security/pre-xss.png),
[post-xss.png](phase1-security/post-xss.png),
[pre-xss-breakout.html](phase1-security/pre-xss-breakout.html),
[post-xss-breakout.html](phase1-security/post-xss-breakout.html),
[pre-xss-breakout.png](phase1-security/pre-xss-breakout.png),
[post-xss-breakout.png](phase1-security/post-xss-breakout.png).

### Phase 2 — data layer

[PR #22](https://github.com/COG-GTM/vantage-telco/pull/22) introduced the
shared lazy Mongo client and lifecycle cleanup, startup indexes, datastore
query push-down, and the invoice account index that removes the billing N+1
scan. Billing output remained byte-identical, with timing and invoice
comparison artifacts documenting the result.

Artifacts: [pre-api.txt](phase2-data-layer/pre-api.txt),
[post-api.txt](phase2-data-layer/post-api.txt),
[pre-capacity.png](phase2-data-layer/pre-capacity.png),
[post-capacity.png](phase2-data-layer/post-capacity.png),
[pre-dashboard-billing-top.png](phase2-data-layer/pre-dashboard-billing-top.png),
[post-dashboard-billing-top.png](phase2-data-layer/post-dashboard-billing-top.png),
[pre-dashboard-billing.png](phase2-data-layer/pre-dashboard-billing.png),
[post-dashboard-billing.png](phase2-data-layer/post-dashboard-billing.png),
[pre-dashboard.png](phase2-data-layer/pre-dashboard.png),
[post-dashboard.png](phase2-data-layer/post-dashboard.png),
[pre-invoices.json](phase2-data-layer/pre-invoices.json),
[post-invoices.json](phase2-data-layer/post-invoices.json),
[post-invoices-diff.txt](phase2-data-layer/post-invoices-diff.txt),
[pre-timing.txt](phase2-data-layer/pre-timing.txt),
[post-timing.txt](phase2-data-layer/post-timing.txt),
[pre-walkthrough.webm](phase2-data-layer/pre-walkthrough.webm),
[post-walkthrough.webm](phase2-data-layer/post-walkthrough.webm),
[post-billing-comparison.png](phase2-data-layer/post-billing-comparison.png).

### Phase 3 — API templating

[PR #24](https://github.com/COG-GTM/vantage-telco/pull/24) added async route
handlers, paginated response envelopes, `/v1` API versioning with deprecated
legacy aliases, and autoescaping Jinja2 templates for the dashboards. The
invoice item payload stayed byte-identical while the API and HTML surfaces
gained their new contracts.

Artifacts: [pre-api.txt](phase3-api-templating/pre-api.txt),
[post-api.txt](phase3-api-templating/post-api.txt),
[pre-capacity.png](phase3-api-templating/pre-capacity.png),
[post-capacity.png](phase3-api-templating/post-capacity.png),
[pre-dashboard-billing.png](phase3-api-templating/pre-dashboard-billing.png),
[post-dashboard-billing.png](phase3-api-templating/post-dashboard-billing.png),
[pre-dashboard.png](phase3-api-templating/pre-dashboard.png),
[post-dashboard.png](phase3-api-templating/post-dashboard.png),
[pre-invoices-page.txt](phase3-api-templating/pre-invoices-page.txt),
[post-invoices-page.txt](phase3-api-templating/post-invoices-page.txt),
[post-invoice-items-diff.txt](phase3-api-templating/post-invoice-items-diff.txt),
[pre-walkthrough.webm](phase3-api-templating/pre-walkthrough.webm),
[post-walkthrough.webm](phase3-api-templating/post-walkthrough.webm).

### Phase 4 — Java 21

[PR #21](https://github.com/COG-GTM/vantage-telco/pull/21) moved the
`vantage-report` Maven module to Temurin Java 21 and replaced its bounded
platform-thread fan-out with virtual threads while preserving deterministic
invoice ordering and rendered output.

Artifacts: [pre-batch-output.txt](phase4-java21/pre-batch-output.txt),
[post-batch-output.txt](phase4-java21/post-batch-output.txt),
[pre-java-version.txt](phase4-java21/pre-java-version.txt),
[post-java-version.txt](phase4-java21/post-java-version.txt),
[pre-mvn-verify.txt](phase4-java21/pre-mvn-verify.txt),
[post-mvn-verify.txt](phase4-java21/post-mvn-verify.txt),
[diff-transcript.txt](phase4-java21/diff-transcript.txt).

### Phase 5 — deployment and supply chain

**This PR** adds file-backed runtime configuration, multi-stage Python and
Java container images, Mongo-backed Docker Compose deployment, secret-store
documentation, SBOM generation, image vulnerability scanning, and final
integration validation. It also adds authenticated pre/post captures for the
deployed code path while preserving the existing billing behavior.

Artifacts: [integration-validation.txt](phase5-deploy/integration-validation.txt),
[docker-compose-transcript.txt](phase5-deploy/docker-compose-transcript.txt),
[post-validation.txt](phase5-deploy/post-validation.txt),
[pre-api.txt](phase5-deploy/pre-api.txt),
[post-api.txt](phase5-deploy/post-api.txt),
[pre-capacity.png](phase5-deploy/pre-capacity.png),
[post-capacity.png](phase5-deploy/post-capacity.png),
[pre-dashboard-billing.png](phase5-deploy/pre-dashboard-billing.png),
[post-dashboard-billing.png](phase5-deploy/post-dashboard-billing.png),
[pre-dashboard.png](phase5-deploy/pre-dashboard.png),
[post-dashboard.png](phase5-deploy/post-dashboard.png),
[pre-walkthrough.webm](phase5-deploy/pre-walkthrough.webm),
[post-walkthrough.webm](phase5-deploy/post-walkthrough.webm).

## Merge order

`#20 → #23 → #22 → #24 → #21 → Phase 5 (this PR)`

## Parity

The `tools/parity` comparison requires `../meridian-telco`, which is absent
from this checkout, so that command was skipped and the absence is recorded
in [post-validation.txt](phase5-deploy/post-validation.txt). Parity is
instead evidenced by the unchanged `tests/test_billing*.py` suite and the
byte-identical invoice diffs in
[phase2 post-invoices-diff.txt](phase2-data-layer/post-invoices-diff.txt),
[phase3 post-invoice-items-diff.txt](phase3-api-templating/post-invoice-items-diff.txt),
and [phase4 diff-transcript.txt](phase4-java21/diff-transcript.txt).
