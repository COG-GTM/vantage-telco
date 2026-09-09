from __future__ import annotations

from contextlib import asynccontextmanager

from fastapi import APIRouter, Depends, FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.db import close_client, ensure_indexes
from app.routers import billing, capacity, dashboard, inventory, network
from app.security import (
    Principal,
    RateLimitMiddleware,
    SecurityHeadersMiddleware,
    cors_origins,
    current_principal,
)
from app.versioning import LegacyRedirectMiddleware

APP_VERSION = "3.0.0"


@asynccontextmanager
async def lifespan(app: FastAPI):
    ensure_indexes()
    yield
    close_client()


app = FastAPI(
    title="Vantage Network Services",
    version=APP_VERSION,
    description="Inventory, management addressing and billing for the Vantage network.",
    redoc_url=None,
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=cors_origins(),
    allow_methods=["GET"],
    allow_headers=["Authorization", "Content-Type"],
    allow_credentials=False,
)
app.add_middleware(RateLimitMiddleware)
app.add_middleware(SecurityHeadersMiddleware)
app.add_middleware(LegacyRedirectMiddleware)

api_v1 = APIRouter(prefix="/v1")
api_v1.include_router(inventory.router)
api_v1.include_router(network.router)
api_v1.include_router(billing.router)
api_v1.include_router(capacity.router)
api_v1.include_router(dashboard.router)


@api_v1.get("/version", tags=["meta"])
async def version(principal: Principal = Depends(current_principal)):  # noqa: B008
    return {"version": app.version}


app.include_router(api_v1)


@app.get("/health")
async def health():
    return {"status": "ok"}
