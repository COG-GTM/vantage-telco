from __future__ import annotations

import argparse
import base64
import hashlib
import hmac
import json
import os
import sys
import threading
import time
from dataclasses import dataclass
from typing import Any

from fastapi import Depends, HTTPException, Request, Security
from fastapi.responses import JSONResponse
from fastapi.security import (
    HTTPAuthorizationCredentials,
    HTTPBearer,
    SecurityScopes,
)
from starlette.middleware.base import BaseHTTPMiddleware

SCOPE_SALES_ENGINEERING = "sales-engineering"
SCOPE_NOC = "noc"
SCOPE_BILLING_OPS = "billing-ops"
ALL_SCOPES = (SCOPE_SALES_ENGINEERING, SCOPE_NOC, SCOPE_BILLING_OPS)
SCOPE_DESCRIPTIONS = {
    SCOPE_SALES_ENGINEERING: "Access sales engineering capacity routes.",
    SCOPE_NOC: "Access network operations and inventory routes.",
    SCOPE_BILLING_OPS: "Access billing routes with PII visibility.",
}

PII_FIELDS = ("tax_id", "legal_name", "service_address")
REDACTED = "[redacted]"


def _secret(secret: str | None = None) -> str:
    value = secret if secret is not None else os.environ.get("VANTAGE_AUTH_DEV_SECRET")
    if not value:
        raise HTTPException(status_code=503, detail="authentication not configured")
    return value


def _encode(value: bytes) -> str:
    return base64.urlsafe_b64encode(value).rstrip(b"=").decode("ascii")


def _decode(value: str) -> bytes:
    return base64.urlsafe_b64decode(value + "=" * (-len(value) % 4))


@dataclass(frozen=True)
class Principal:
    sub: str
    scopes: frozenset[str]

    def has(self, scope: str) -> bool:
        return scope in self.scopes


def mint_token(
    sub: str,
    scopes: list[str] | tuple[str, ...] | set[str],
    ttl_seconds: int = 3600,
    secret: str | None = None,
) -> str:
    signing_secret = _secret(secret)
    if not isinstance(sub, str) or not sub:
        raise ValueError("sub must be a non-empty string")
    scope_list = list(scopes)
    if any(scope not in ALL_SCOPES for scope in scope_list):
        raise ValueError("unknown scope")
    payload = {
        "sub": sub,
        "scopes": scope_list,
        "exp": int(time.time()) + ttl_seconds,
    }
    payload_b64 = _encode(
        json.dumps(payload, separators=(",", ":"), sort_keys=True).encode("utf-8")
    )
    signature = _encode(
        hmac.new(
            signing_secret.encode("utf-8"), payload_b64.encode("ascii"), hashlib.sha256
        ).digest()
    )
    return f"{payload_b64}.{signature}"


def verify_token(token: str, secret: str | None = None) -> Principal:
    signing_secret = _secret(secret)
    try:
        payload_b64, signature_b64 = token.split(".")
        payload_bytes = _decode(payload_b64)
        provided_signature = _decode(signature_b64)
        expected_signature = hmac.new(
            signing_secret.encode("utf-8"), payload_b64.encode("ascii"), hashlib.sha256
        ).digest()
        if not hmac.compare_digest(provided_signature, expected_signature):
            raise ValueError("invalid signature")
        payload: Any = json.loads(payload_bytes)
        sub = payload["sub"]
        scopes = payload["scopes"]
        exp = payload["exp"]
        if (
            not isinstance(sub, str)
            or not sub
            or not isinstance(scopes, list)
            or not isinstance(exp, int)
            or isinstance(exp, bool)
        ):
            raise ValueError("invalid payload")
        if any(not isinstance(scope, str) or scope not in ALL_SCOPES for scope in scopes):
            raise ValueError("unknown scope")
        if exp <= int(time.time()):
            raise ValueError("token expired")
        return Principal(sub=sub, scopes=frozenset(scopes))
    except (KeyError, TypeError, ValueError, json.JSONDecodeError, UnicodeDecodeError) as exc:
        if isinstance(exc, ValueError) and str(exc) in {
            "invalid signature",
            "invalid payload",
            "unknown scope",
            "token expired",
        }:
            raise
        raise ValueError("invalid token") from exc


bearer = HTTPBearer(
    auto_error=False,
    scheme_name="BearerToken",
    description="Bearer token scopes: "
    + ", ".join(f"{scope} ({description})" for scope, description in SCOPE_DESCRIPTIONS.items()),
)


def _unauthorized() -> HTTPException:
    return HTTPException(
        status_code=401,
        detail="invalid authentication credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )


def current_principal(
    security_scopes: SecurityScopes,
    credentials: HTTPAuthorizationCredentials | None = Depends(bearer),  # noqa: B008
) -> Principal:
    if credentials is None:
        raise _unauthorized()
    try:
        principal = verify_token(credentials.credentials)
    except ValueError as exc:
        raise _unauthorized() from exc
    if security_scopes.scopes and not any(principal.has(scope) for scope in security_scopes.scopes):
        raise HTTPException(status_code=403, detail="insufficient scope")
    return principal


def ops_principal(
    principal: Principal = Security(  # noqa: B008
        current_principal, scopes=[SCOPE_NOC, SCOPE_BILLING_OPS]
    ),
) -> Principal:
    return principal


def sales_principal(
    principal: Principal = Security(  # noqa: B008
        current_principal, scopes=[SCOPE_SALES_ENGINEERING]
    ),
) -> Principal:
    return principal


def redact_invoice(invoice: dict, principal: Principal) -> dict:
    if principal.has(SCOPE_BILLING_OPS):
        return invoice
    redacted = dict(invoice)
    for field in PII_FIELDS:
        redacted[field] = REDACTED
    return redacted


def redact_invoices(invoices, principal: Principal) -> list[dict]:
    return [redact_invoice(invoice, principal) for invoice in invoices]


class TokenBucketRateLimiter:
    def __init__(self, limit_per_minute: int) -> None:
        self.limit_per_minute = limit_per_minute
        self._requests: dict[str, list[float]] = {}
        self._lock = threading.Lock()

    def allow(self, key: str) -> bool:
        if self.limit_per_minute == 0:
            return True
        now = time.monotonic()
        with self._lock:
            requests = [stamp for stamp in self._requests.get(key, []) if now - stamp < 60]
            if len(requests) >= self.limit_per_minute:
                self._requests[key] = requests
                return False
            requests.append(now)
            self._requests[key] = requests
            return True

    def reset(self) -> None:
        with self._lock:
            self._requests.clear()


rate_limiter = TokenBucketRateLimiter(int(os.environ.get("VANTAGE_RATE_LIMIT_PER_MINUTE", "120")))


class RateLimitMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        if request.url.path != "/health":
            client = request.client
            key = client.host if client is not None else "unknown"
            if not rate_limiter.allow(key):
                return JSONResponse(
                    status_code=429,
                    content={"detail": "rate limit exceeded"},
                    headers={"Retry-After": "60"},
                )
        return await call_next(request)


class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        response = await call_next(request)
        response.headers.update(
            {
                "Strict-Transport-Security": "max-age=31536000; includeSubDomains",
                "Content-Security-Policy": (
                    "default-src 'self'; script-src 'self' 'unsafe-inline' "
                    "https://cdn.jsdelivr.net; style-src 'self' 'unsafe-inline' "
                    "https://cdn.jsdelivr.net; img-src 'self' data: "
                    "https://fastapi.tiangolo.com; frame-ancestors 'none'"
                ),
                "X-Content-Type-Options": "nosniff",
                "X-Frame-Options": "DENY",
                "Referrer-Policy": "no-referrer",
            }
        )
        return response


def cors_origins() -> list[str]:
    return [
        origin.strip()
        for origin in os.environ.get("VANTAGE_CORS_ORIGINS", "").split(",")
        if origin.strip()
    ]


def _cli() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--scopes", nargs="+", required=True)
    parser.add_argument("--sub", default="dev-user")
    parser.add_argument("--ttl", type=int, default=3600)
    args = parser.parse_args()
    secret = os.environ.get("VANTAGE_AUTH_DEV_SECRET")
    if not secret:
        print("VANTAGE_AUTH_DEV_SECRET is required", file=sys.stderr)
        return 2
    try:
        print(mint_token(args.sub, args.scopes, ttl_seconds=args.ttl, secret=secret))
    except ValueError as exc:
        print(str(exc), file=sys.stderr)
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(_cli())
