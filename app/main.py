from __future__ import annotations

from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.db import close_client, ensure_indexes
from app.routers import billing, capacity, dashboard, inventory, network
from app.security import RateLimitMiddleware, SecurityHeadersMiddleware, cors_origins


@asynccontextmanager
async def lifespan(app: FastAPI):
    ensure_indexes()
    yield
    close_client()


app = FastAPI(
    title="Vantage Network Services",
    version="2.4.0",
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

app.include_router(inventory.router)
app.include_router(network.router)
app.include_router(billing.router)
app.include_router(capacity.router)
app.include_router(dashboard.router)


@app.get("/health")
def health():
    return {"status": "ok"}
