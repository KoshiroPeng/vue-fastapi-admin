from datetime import datetime
from enum import Enum
from typing import Protocol

from pydantic import BaseModel, Field


class NCEHealthStatus(str, Enum):
    HEALTHY = "healthy"
    DEGRADED = "degraded"
    DOWN = "down"


class NCEHealth(BaseModel):
    status: NCEHealthStatus
    mode: str
    configured: bool
    latency_ms: int = Field(ge=0)
    message: str


class NCEGuestCreateRequest(BaseModel):
    request_id: str = Field(min_length=1, max_length=64)
    username_prefix: str = Field(pattern=r"^[a-z][a-z0-9_]{1,15}$")
    valid_duration_minutes: int = Field(gt=0, le=10080)
    max_devices: int = Field(gt=0, le=10)
    description: str = Field(min_length=1, max_length=128)


class NCEGuest(BaseModel):
    username: str
    password: str
    valid_until: datetime
    max_devices: int


class NCEClient(Protocol):
    async def health(self) -> NCEHealth:
        """Return a side-effect-free dependency health snapshot."""

    async def create_guest(self, request: NCEGuestCreateRequest) -> NCEGuest:
        """Create a temporary NCE guest through the selected adapter."""
