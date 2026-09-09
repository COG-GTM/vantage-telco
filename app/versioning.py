from fastapi import Request
from fastapi.responses import RedirectResponse
from starlette.middleware.base import BaseHTTPMiddleware

LEGACY_PREFIXES = (
    "/resources",
    "/circuits",
    "/billing",
    "/network",
    "/capacity",
    "/dashboard",
)


class LegacyRedirectMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        path = request.url.path
        if any(path == prefix or path.startswith(f"{prefix}/") for prefix in LEGACY_PREFIXES):
            query = f"?{request.url.query}" if request.url.query else ""
            return RedirectResponse(url=f"/v1{path}{query}", status_code=308)
        return await call_next(request)
