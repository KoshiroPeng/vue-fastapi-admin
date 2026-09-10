import time
from enum import Enum

from pydantic import BaseModel, ConfigDict, Field
from redis.exceptions import RedisError

from app.core.redis import redis_manager
from app.core.request_context import get_request_id
from app.log import logger
from app.settings import settings


class DependencyHealthStatus(str, Enum):
    HEALTHY = "healthy"
    DEGRADED = "degraded"
    DOWN = "down"


class DependencyHealth(BaseModel):
    model_config = ConfigDict(frozen=True)

    status: DependencyHealthStatus
    configured: bool
    latency_ms: int = Field(ge=0)
    message: str


async def get_redis_health() -> DependencyHealth:
    started = time.perf_counter()
    try:
        await redis_manager.client.ping()
    except (RedisError, RuntimeError):
        latency_ms = max(0, int((time.perf_counter() - started) * 1000))
        logger.warning("event=redis_health_failed request_id={}", get_request_id() or "-")
        return DependencyHealth(
            status=DependencyHealthStatus.DOWN,
            configured=bool(settings.REDIS_URL),
            latency_ms=latency_ms,
            message="Redis 服务不可用",
        )
    latency_ms = max(0, int((time.perf_counter() - started) * 1000))
    return DependencyHealth(
        status=DependencyHealthStatus.HEALTHY,
        configured=True,
        latency_ms=latency_ms,
        message="Redis 服务可用",
    )
