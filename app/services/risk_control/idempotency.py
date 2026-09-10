import hashlib

from redis.asyncio import Redis

from .errors import IdempotencyConflict


class RedisIdempotencyGuard:
    """Reserve request keys so a retried POST cannot execute twice."""

    def __init__(self, redis: Redis, key_prefix: str = "wifi:idempotency") -> None:
        self._redis = redis
        self._key_prefix = key_prefix.rstrip(":")

    async def claim(self, scope: str, idempotency_key: str, ttl_seconds: int) -> None:
        if not scope or len(scope) > 64:
            raise ValueError("scope 长度必须在 1 到 64 之间")
        if not idempotency_key or len(idempotency_key) > 128:
            raise ValueError("Idempotency-Key 长度必须在 1 到 128 之间")
        if ttl_seconds <= 0:
            raise ValueError("ttl_seconds must be greater than zero")
        digest = hashlib.sha256(f"{scope}:{idempotency_key}".encode("utf-8")).hexdigest()
        claimed = await self._redis.set(f"{self._key_prefix}:{digest}", "reserved", ex=ttl_seconds, nx=True)
        if not claimed:
            raise IdempotencyConflict("Idempotency-Key 已被使用")
