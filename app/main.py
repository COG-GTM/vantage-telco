from __future__ import annotations

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI

from app import db
from app.routers import billing, capacity, dashboard, inventory, network


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

app.include_router(inventory.router)
app.include_router(network.router)
app.include_router(billing.router)
app.include_router(capacity.router)
app.include_router(dashboard.router)


@app.get("/health")
def health():
    return {"status": "ok"}
