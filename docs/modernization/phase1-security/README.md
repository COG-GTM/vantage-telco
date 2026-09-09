# Phase 1: Security

Phase 1 adds bearer-token authentication, scope-based authorization, response
PII redaction, reflected-XSS escaping, browser security headers, CORS
configuration, and a fixed-window request limit.

## Configuration

The application reads these environment variables at startup:

| Variable | Purpose |
| --- | --- |
| `VANTAGE_OIDC_ISSUER` | JWT issuer, default `https://idp.vantage.local/` |
| `VANTAGE_OIDC_AUDIENCE` | JWT audience, default `vantage-net` |
| `VANTAGE_OIDC_JWKS_URL` | OIDC JWKS URL for production token verification |
| `VANTAGE_OIDC_AUTHORIZATION_URL` | OAuth authorization URL |
| `VANTAGE_OIDC_TOKEN_URL` | OAuth token URL |
| `VANTAGE_AUTH_DEV_SECRET` | HS256 secret for local development and tests |
| `VANTAGE_AUTH_LEEWAY_SECONDS` | JWT time-validation leeway, default `30` |
| `VANTAGE_CORS_ORIGINS` | Comma-separated allowed origins; empty means none |
| `VANTAGE_RATE_LIMIT_PER_MINUTE` | Per-client fixed-window limit, default `120`; `0` disables |
| `VANTAGE_TRUST_PROXY` | Set to `1` to use the first `X-Forwarded-For` hop |

Production deployments should use `VANTAGE_OIDC_JWKS_URL` and should not use a
development secret. The `/health` endpoint remains open. All other endpoints
require a bearer token with at least one scope listed below.

## Scope-to-router matrix

| Router | Required scopes (any one) |
| --- | --- |
| Inventory (`/resources`, `/circuits`) | `inventory:read`, `noc` |
| Network (`/network/*`) | `network:read`, `noc` |
| Capacity (`/capacity*`) | `sales-engineering` |
| Billing (`/billing/*`) | `billing-ops`, `noc` |
| Dashboards (`/dashboard*`) | `noc`, `billing-ops` |

Billing operations receive invoice PII unchanged. NOC responses redact
`tax_id`, `legal_name`, and `service_address` as `[redacted]`. Other invoice
fields remain unchanged.

## Local development token

```bash
VANTAGE_AUTH_DEV_SECRET=dev .venv/bin/python -m app.security \
  --scopes billing-ops noc sales-engineering
```

Use the resulting value as an HTTP header:

```text
Authorization: Bearer <token>
```

## Captures

The main capture script and the extra security capture accept a bearer token:

```bash
.venv/bin/python docs/modernization/capture.py \
  docs/modernization/phase1-security post --bearer "$TOKEN"
.venv/bin/python docs/modernization/phase1-security/capture_extra.py \
  post --bearer "$TOKEN"
```

The artifact set contains `pre-` and `post-` captures:

- `dashboard.png`, `dashboard-billing.png`, `capacity.png`
- `walkthrough.webm`
- `api.txt`
- `xss.html`, `xss.png`
- `xss-breakout.html`, `xss-breakout.png`
- `auth.txt`

The XSS captures exercise both a normal reflected payload and an attribute
breakout payload. The auth transcript records unauthenticated and bearer
requests, including response security headers.
