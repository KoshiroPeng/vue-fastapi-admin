import os
from uuid import uuid4

import pytest
from redis.asyncio import Redis

from app.services.risk_control import (
    IdempotencyConflict,
    RateLimitExceeded,
    RedisIdempotencyGuard,
    RedisReplayProtector,
    RedisSlidingWindowRateLimiter,
    ReplayDetected,
)

pytestmark = pytest.mark.skipif(
    os.getenv("RUN_REDIS_INTEGRATION") != "1",
    reason="set RUN_REDIS_INTEGRATION=1 to test against an available Redis",
)


@pytest.mark.asyncio
async def test_nonce_is_claimed_once_without_storing_raw_value() -> None:
    redis_url = os.getenv("REDIS_TEST_URL", "redis://127.0.0.1:16379/0")
    client = Redis.from_url(redis_url, decode_responses=True)
    key_prefix = f"test:wifi:nonce:{uuid4().hex}"
    protector = RedisReplayProtector(client, key_prefix=key_prefix)
    nonce = "nonce-that-must-not-appear-in-redis-key"

    try:
        await protector.claim("kiosk", nonce, ttl_seconds=60)
        keys = await client.keys(f"{key_prefix}:*")

        assert len(keys) == 1
        assert nonce not in keys[0]
        with pytest.raises(ReplayDetected):
            await protector.claim("kiosk", nonce, ttl_seconds=60)
    finally:
        keys = await client.keys(f"{key_prefix}:*")
        if keys:
            await client.delete(*keys)
        await client.aclose()


@pytest.mark.asyncio
async def test_sliding_window_rate_limit_rejects_excess_requests() -> None:
    redis_url = os.getenv("REDIS_TEST_URL", "redis://127.0.0.1:16379/0")
    client = Redis.from_url(redis_url, decode_responses=True)
    key_prefix = f"test:wifi:rate:{uuid4().hex}"
    limiter = RedisSlidingWindowRateLimiter(client, key_prefix=key_prefix)
    subject_hash = "a" * 64

    try:
        first = await limiter.check("kiosk", subject_hash, limit=2, window_seconds=60, now_ms=1_000_000)
        second = await limiter.check("kiosk", subject_hash, limit=2, window_seconds=60, now_ms=1_000_001)

        assert first.remaining == 1
        assert second.remaining == 0
        with pytest.raises(RateLimitExceeded) as exc_info:
            await limiter.check("kiosk", subject_hash, limit=2, window_seconds=60, now_ms=1_000_002)
        assert exc_info.value.retry_after_seconds == 60
        recovered = await limiter.check("kiosk", subject_hash, limit=2, window_seconds=60, now_ms=1_060_001)
        assert recovered.remaining == 1
    finally:
        keys = await client.keys(f"{key_prefix}:*")
        if keys:
            await client.delete(*keys)
        await client.aclose()


@pytest.mark.asyncio
async def test_idempotency_key_is_reserved_once_without_storing_raw_key() -> None:
    redis_url = os.getenv("REDIS_TEST_URL", "redis://127.0.0.1:16379/0")
    client = Redis.from_url(redis_url, decode_responses=True)
    key_prefix = f"test:wifi:idempotency:{uuid4().hex}"
    guard = RedisIdempotencyGuard(client, key_prefix=key_prefix)
    idempotency_key = "idempotency-key-that-must-not-appear-in-redis"

    try:
        await guard.claim("kiosk", idempotency_key, ttl_seconds=60)
        keys = await client.keys(f"{key_prefix}:*")

        assert len(keys) == 1
        assert idempotency_key not in keys[0]
        with pytest.raises(IdempotencyConflict):
            await guard.claim("kiosk", idempotency_key, ttl_seconds=60)
    finally:
        keys = await client.keys(f"{key_prefix}:*")
        if keys:
            await client.delete(*keys)
        await client.aclose()
