from __future__ import annotations

import math
import os
import threading
import time
from typing import Any

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import JSONResponse, Response


class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    """Add browser and transport security headers to every response."""

    _HEADERS = {
        "Strict-Transport-Security": "max-age=63072000; includeSubDomains",
        "Content-Security-Policy": (
            "default-src 'self'; script-src 'self' 'unsafe-inline' https://cdn.jsdelivr.net; "
            "style-src 'self' 'unsafe-inline' https://fonts.googleapis.com "
            "https://cdn.jsdelivr.net; "
            "font-src 'self' https://fonts.gstatic.com; img-src 'self' data: "
            "https://fastapi.tiangolo.com; frame-ancestors 'none'; base-uri 'self'; "
            "form-action 'self'"
        ),
        "X-Content-Type-Options": "nosniff",
        "X-Frame-Options": "DENY",
        "Referrer-Policy": "no-referrer",
    }

    async def dispatch(self, request: Request, call_next: Any) -> Response:
        response = await call_next(request)
        for name, value in self._HEADERS.items():
            response.headers[name] = value
        return response


class RateLimitMiddleware(BaseHTTPMiddleware):
    """Apply a fixed-window request limit per client."""

    def __init__(
        self,
        app: Any,
        limit_per_minute: int | None = None,
        trust_proxy: bool | None = None,
    ) -> None:
        super().__init__(app)
        self.limit_per_minute = (
            int(os.environ.get("VANTAGE_RATE_LIMIT_PER_MINUTE", "120"))
            if limit_per_minute is None
            else limit_per_minute
        )
        self.trust_proxy = (
            os.environ.get("VANTAGE_TRUST_PROXY") == "1"
            if trust_proxy is None
            else trust_proxy
        )
        self._windows: dict[str, tuple[int, int]] = {}
        self._lock = threading.Lock()

    def _client_key(self, request: Request) -> str:
        if self.trust_proxy:
            forwarded = request.headers.get("x-forwarded-for")
            if forwarded:
                return forwarded.split(",", 1)[0].strip() or "unknown"
        client = request.scope.get("client")
        return client[0] if client else "unknown"

    async def dispatch(self, request: Request, call_next: Any) -> Response:
        if self.limit_per_minute <= 0:
            return await call_next(request)

        now = time.time()
        window_start = int(now // 60) * 60
        window_end = window_start + 60
        key = self._client_key(request)

        if request.url.path == "/health":
            response = await call_next(request)
            response.headers["X-RateLimit-Limit"] = str(self.limit_per_minute)
            response.headers["X-RateLimit-Remaining"] = str(self.limit_per_minute)
            return response

        with self._lock:
            if len(self._windows) > 10_000:
                self._windows = {
                    client: value
                    for client, value in self._windows.items()
                    if value[0] == window_start
                }
            current_window, count = self._windows.get(key, (window_start, 0))
            if current_window != window_start:
                count = 0
            if count >= self.limit_per_minute:
                remaining = 0
                retry_after = max(1, math.ceil(window_end - now))
                response = JSONResponse(
                    {"detail": "rate limit exceeded"},
                    status_code=429,
                    headers={"Retry-After": str(retry_after)},
                )
            else:
                count += 1
                self._windows[key] = (window_start, count)
                remaining = self.limit_per_minute - count
                response = None

        if response is None:
            response = await call_next(request)
        response.headers["X-RateLimit-Limit"] = str(self.limit_per_minute)
        response.headers["X-RateLimit-Remaining"] = str(remaining)
        return response
