from __future__ import annotations

import os
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app import db
from app.middleware import RateLimitMiddleware, SecurityHeadersMiddleware
from app.routers import billing, capacity, dashboard, inventory, network


def cors_origins() -> list[str]:
    return [
        origin.strip()
        for origin in os.environ.get("VANTAGE_CORS_ORIGINS", "").split(",")
        if origin.strip()
    ]


@asynccontextmanager
async def lifespan(_: FastAPI) -> AsyncIterator[None]:
    db.ensure_indexes()
    try:
        yield
    finally:
        db.close_client()


app = FastAPI(
    lifespan=lifespan,
    title="Vantage Network Services",
    version="2.4.0",
    description="Inventory, management addressing and billing for the Vantage network.",
)

app.add_middleware(RateLimitMiddleware)
app.add_middleware(
    CORSMiddleware,
    allow_origins=cors_origins(),
    allow_methods=["GET"],
    allow_headers=["Authorization", "Content-Type"],
    allow_credentials=False,
)
app.add_middleware(SecurityHeadersMiddleware)

app.include_router(inventory.router)
app.include_router(network.router)
app.include_router(billing.router)
app.include_router(capacity.router)
app.include_router(dashboard.router)


@app.get("/health")
def health():
    return {"status": "ok"}
