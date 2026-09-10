import os

import pytest

from app.core.redis import RedisConnectionManager

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
