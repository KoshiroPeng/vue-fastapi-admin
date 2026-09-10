import os

import pytest

from app.core.redis import RedisConnectionManager, redis_manager
from app.services.health import DependencyHealthStatus, get_redis_health

pytestmark = pytest.mark.skipif(
    os.getenv("RUN_REDIS_INTEGRATION") != "1",
    reason="set RUN_REDIS_INTEGRATION=1 to test against an available Redis",
)


@pytest.mark.asyncio
async def test_redis_connection_manager_connects_and_closes_cleanly() -> None:
    redis_url = os.getenv("REDIS_TEST_URL", "redis://127.0.0.1:16379/0")
    manager = RedisConnectionManager(redis_url)

    await manager.connect()
    assert await manager.client.ping() is True

    await manager.close()
    with pytest.raises(RuntimeError, match="尚未连接"):
        _ = manager.client


@pytest.mark.asyncio
async def test_global_redis_health_reports_live_wsl_connection() -> None:
    await redis_manager.connect()
    try:
        health = await get_redis_health()
        assert health.status is DependencyHealthStatus.HEALTHY
        assert health.configured is True
    finally:
        await redis_manager.close()
