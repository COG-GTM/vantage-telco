from __future__ import annotations

from pydantic import BaseModel

LIFECYCLE_STATES = ("ACTIVE", "MAINTENANCE", "RETIRED", "PLANNED", "RESERVED")


class Resource(BaseModel):
    device_uuid: str
    name: str
    market_id: str
    lifecycle_state: str
    latitude: float
    longitude: float
    tower_registration: str | None = None
    total_capacity_mbps: int = 0
    allocated_mbps: int = 0
    maintenance_buffer_mbps: int = 0
    available_mbps: int = 0
    utilization_pct: float = 0.0


class Circuit(BaseModel):
    circuit_id: str
    name: str
    a_device_uuid: str
    z_device_uuid: str
    capacity_mbps: int
    allocated_mbps: int
    maintenance_buffer_mbps: int = 0
    role: str
    lifecycle_state: str
    available_mbps: int = 0
