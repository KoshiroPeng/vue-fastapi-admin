import asyncio
import os
from uuid import uuid4

import pytest
from pydantic import BaseModel, ConfigDict
from redis.asyncio import Redis

from app.services.dashboard.cache import RedisQueryCache

pytestmark = pytest.mark.skipif(
    os.getenv("RUN_REDIS_INTEGRATION") != "1",
    reason="set RUN_REDIS_INTEGRATION=1 to test against an available Redis",
)


class CachedResult(BaseModel):
    model_config = ConfigDict(frozen=True)

    value: str


@pytest.mark.asyncio
async def test_redis_query_cache_merges_concurrent_loads_and_hides_query_values() -> None:
    redis_url = os.getenv("REDIS_TEST_URL", "redis://127.0.0.1:16379/0")
    redis = Redis.from_url(redis_url, decode_responses=True)
    prefix = f"test:wifi:dashboard-cache:{uuid4().hex}"
    cache = RedisQueryCache(redis, key_prefix=prefix)
    calls = 0

    async def load() -> CachedResult:
        nonlocal calls
        calls += 1
        await asyncio.sleep(0.01)
        return CachedResult(value="loaded")

    try:
        results = await asyncio.gather(
            *[
                cache.get_or_load(
                    namespace="online-users",
                    key_data={"user_name": "sensitive-account"},
                    ttl_seconds=30,
                    model=CachedResult,
                    loader=load,
                )
                for _ in range(5)
            ]
        )
        cached = await cache.get_or_load(
            namespace="online-users",
            key_data={"user_name": "sensitive-account"},
            ttl_seconds=30,
            model=CachedResult,
            loader=load,
        )
        keys = await redis.keys(f"{prefix}:*")

        assert calls == 1
        assert all(item.value == "loaded" for item in results)
        assert cached.value == "loaded"
        assert len(keys) == 1
        assert "sensitive-account" not in keys[0]
    finally:
        keys = await redis.keys(f"{prefix}:*")
        if keys:
            await redis.delete(*keys)
        await redis.aclose()
