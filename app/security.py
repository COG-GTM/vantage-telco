"""OAuth2 / OIDC bearer-token authentication and scope-based authorization.

Tokens are JWTs issued by an external OIDC identity provider. In production the
provider's JWKS endpoint (``VANTAGE_OIDC_JWKS_URL``) supplies the RS256/ES256
verification keys; for local development and tests an HS256 shared secret
(``VANTAGE_AUTH_DEV_SECRET``) may be used instead. There is no user store here.

Usage in a router::

    router = APIRouter(dependencies=[Security(require_scopes, scopes=[SCOPE_BILLING_OPS])])

Mint a local development token::

    VANTAGE_AUTH_DEV_SECRET=dev python -m app.security --scopes billing-ops noc
"""

from __future__ import annotations

import argparse
import time
from dataclasses import dataclass, field
from functools import lru_cache

import jwt
from fastapi import Depends, HTTPException, Request, status
from fastapi.security import OAuth2AuthorizationCodeBearer, SecurityScopes
from jwt import PyJWKClient

from app.config import setting

SCOPE_INVENTORY_READ = "inventory:read"
SCOPE_NETWORK_READ = "network:read"
SCOPE_SALES_ENGINEERING = "sales-engineering"
SCOPE_NOC = "noc"
SCOPE_BILLING_OPS = "billing-ops"

SCOPE_DESCRIPTIONS = {
    SCOPE_INVENTORY_READ: "Read resources and circuits",
    SCOPE_NETWORK_READ: "Read management addressing",
    SCOPE_SALES_ENGINEERING: "Capacity checks and quoting",
    SCOPE_NOC: "Operations dashboards (PII redacted)",
    SCOPE_BILLING_OPS: "Billing operations including customer PII",
}
ALL_SCOPES = tuple(SCOPE_DESCRIPTIONS)

PII_FIELDS = ("tax_id", "legal_name", "service_address")
REDACTED = "[redacted]"

_ALLOWED_ALGORITHMS = [
    "RS256",
    "RS384",
    "RS512",
    "ES256",
    "ES384",
    "ES512",
    "PS256",
    "PS384",
]
_DEV_ALGORITHM = "HS256"


@dataclass(frozen=True)
class AuthSettings:
    issuer: str
    audience: str
    jwks_url: str | None
    dev_secret: str | None
    authorization_url: str
    token_url: str
    leeway_seconds: int = 30

    @classmethod
    def from_env(cls) -> AuthSettings:
        issuer = _setting_with_default("VANTAGE_OIDC_ISSUER", "https://idp.vantage.local/")
        return cls(
            issuer=issuer,
            audience=_setting_with_default("VANTAGE_OIDC_AUDIENCE", "vantage-net"),
            jwks_url=setting("VANTAGE_OIDC_JWKS_URL") or None,
            dev_secret=setting("VANTAGE_AUTH_DEV_SECRET") or None,
            authorization_url=_setting_with_default(
                "VANTAGE_OIDC_AUTHORIZATION_URL", issuer.rstrip("/") + "/authorize"
            ),
            token_url=_setting_with_default(
                "VANTAGE_OIDC_TOKEN_URL", issuer.rstrip("/") + "/token"
            ),
            leeway_seconds=int(setting("VANTAGE_AUTH_LEEWAY_SECONDS", "30") or "30"),
        )


def _setting_with_default(name: str, default: str) -> str:
    value = setting(name)
    return default if value is None else value


@lru_cache(maxsize=1)
def settings() -> AuthSettings:
    return AuthSettings.from_env()


@lru_cache(maxsize=1)
def _jwks_client() -> PyJWKClient:
    url = settings().jwks_url
    if url is None:  # pragma: no cover - guarded by _verification_key
        raise RuntimeError("VANTAGE_OIDC_JWKS_URL is not configured")
    return PyJWKClient(url, cache_keys=True, lifespan=600)


def reset_settings_cache() -> None:
    """Re-read configuration from the environment (tests, config reload)."""
    settings.cache_clear()
    _jwks_client.cache_clear()


@dataclass(frozen=True)
class Principal:
    subject: str
    scopes: frozenset[str] = field(default_factory=frozenset)
    claims: dict = field(default_factory=dict, compare=False)

    def has_scope(self, scope: str) -> bool:
        return scope in self.scopes

    def has_any(self, *scopes: str) -> bool:
        return any(s in self.scopes for s in scopes)


oauth2_scheme = OAuth2AuthorizationCodeBearer(
    authorizationUrl=settings().authorization_url,
    tokenUrl=settings().token_url,
    scopes=SCOPE_DESCRIPTIONS,
    auto_error=False,
)


def _unauthorized(detail: str, scopes: SecurityScopes | None = None) -> HTTPException:
    value = "Bearer"
    if scopes and scopes.scopes:
        value = f'Bearer scope="{scopes.scope_str}"'
    return HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail=detail,
        headers={"WWW-Authenticate": value},
    )


def _forbidden(scopes: SecurityScopes) -> HTTPException:
    return HTTPException(
        status_code=status.HTTP_403_FORBIDDEN,
        detail="insufficient scope",
        headers={
            "WWW-Authenticate": (
                f'Bearer scope="{scopes.scope_str}" error="insufficient_scope"'
            )
        },
    )


def _verification_key(token: str) -> tuple[str | bytes, list[str]]:
    cfg = settings()
    if cfg.jwks_url:
        return _jwks_client().get_signing_key_from_jwt(token).key, _ALLOWED_ALGORITHMS
    if cfg.dev_secret:
        return cfg.dev_secret, [_DEV_ALGORITHM]
    raise RuntimeError(
        "no token verification key: set VANTAGE_OIDC_JWKS_URL or VANTAGE_AUTH_DEV_SECRET"
    )


def extract_scopes(claims: dict) -> frozenset[str]:
    """Scopes from the RFC 8693 ``scope`` string or IdP-specific ``scp``/``roles`` lists."""
    found: set[str] = set()
    scope = claims.get("scope")
    if isinstance(scope, str):
        found.update(scope.split())
    elif isinstance(scope, list):
        found.update(str(s) for s in scope)
    for claim in ("scp", "roles"):
        values = claims.get(claim)
        if isinstance(values, list):
            found.update(str(v) for v in values)
        elif isinstance(values, str):
            found.update(values.split())
    return frozenset(found)


def decode_token(token: str) -> Principal:
    """Validate signature, expiry, issuer and audience; return the caller's principal."""
    cfg = settings()
    try:
        key, algorithms = _verification_key(token)
        claims = jwt.decode(
            token,
            key,
            algorithms=algorithms,
            audience=cfg.audience,
            issuer=cfg.issuer,
            leeway=cfg.leeway_seconds,
            options={"require": ["exp", "iat", "sub", "aud", "iss"]},
        )
    except jwt.ExpiredSignatureError as exc:
        raise _unauthorized("token expired") from exc
    except jwt.PyJWTError as exc:
        raise _unauthorized("invalid token") from exc
    return Principal(subject=str(claims["sub"]), scopes=extract_scopes(claims), claims=claims)


def current_principal(
    request: Request, token: str | None = Depends(oauth2_scheme)
) -> Principal:
    """Authenticate the request; 401 when no valid bearer token is present."""
    cached = getattr(request.state, "principal", None)
    if isinstance(cached, Principal):
        return cached
    if not token:
        raise _unauthorized("not authenticated")
    principal = decode_token(token)
    request.state.principal = principal
    return principal


def require_scopes(
    security_scopes: SecurityScopes,
    request: Request,
    token: str | None = Depends(oauth2_scheme),
) -> Principal:
    """Dependency for ``Security(require_scopes, scopes=[...])``.

    The caller must hold at least ONE of the requested scopes (roles are
    alternatives: e.g. ``noc`` or ``billing-ops`` may both view the dashboard).
    """
    try:
        principal = current_principal(request, token)
    except HTTPException as exc:
        if exc.status_code == status.HTTP_401_UNAUTHORIZED:
            raise _unauthorized(str(exc.detail), security_scopes) from exc
        raise
    if security_scopes.scopes and not principal.has_any(*security_scopes.scopes):
        raise _forbidden(security_scopes)
    return principal


def redact_pii(record: dict, principal: Principal) -> dict:
    """Return a copy of an invoice with PII fields blanked unless caller is billing-ops."""
    if principal.has_scope(SCOPE_BILLING_OPS):
        return record
    return {k: (REDACTED if k in PII_FIELDS else v) for k, v in record.items()}


def mint_dev_token(
    scopes: list[str] | tuple[str, ...],
    subject: str = "dev-user",
    ttl_seconds: int = 3600,
    secret: str | None = None,
) -> str:
    """Sign an HS256 development token with ``VANTAGE_AUTH_DEV_SECRET``. Not for production."""
    cfg = settings()
    key = secret or cfg.dev_secret
    if not key:
        raise RuntimeError("VANTAGE_AUTH_DEV_SECRET must be set to mint a dev token")
    now = int(time.time())
    claims = {
        "iss": cfg.issuer,
        "aud": cfg.audience,
        "sub": subject,
        "iat": now,
        "exp": now + ttl_seconds,
        "scope": " ".join(scopes),
    }
    return jwt.encode(claims, key, algorithm=_DEV_ALGORITHM)


def _main() -> None:  # pragma: no cover - CLI helper
    ap = argparse.ArgumentParser(description="Mint a local development bearer token.")
    ap.add_argument("--scopes", nargs="+", default=list(ALL_SCOPES), choices=ALL_SCOPES)
    ap.add_argument("--subject", default="dev-user")
    ap.add_argument("--ttl", type=int, default=3600, help="lifetime in seconds")
    args = ap.parse_args()
    print(mint_dev_token(args.scopes, subject=args.subject, ttl_seconds=args.ttl))


if __name__ == "__main__":  # pragma: no cover
    _main()
