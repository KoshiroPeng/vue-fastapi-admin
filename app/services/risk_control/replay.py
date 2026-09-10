import hashlib

from redis.asyncio import Redis

from .errors import ReplayDetected, RequestExpired


def validate_request_timestamp(timestamp: int, now: int, max_skew_seconds: int) -> None:
    if max_skew_seconds <= 0:
        raise ValueError("max_skew_seconds must be greater than zero")
    if timestamp <= 0 or abs(now - timestamp) > max_skew_seconds:
        raise RequestExpired("请求时间戳已过期或超出允许时钟偏差")


class RedisReplayProtector:
    def __init__(self, redis: Redis, key_prefix: str = "wifi:nonce") -> None:
        self._redis = redis
        self._key_prefix = key_prefix.rstrip(":")

    async def claim(self, scope: str, nonce: str, ttl_seconds: int) -> None:
        if not scope or len(scope) > 64:
            raise ValueError("scope 长度必须在 1 到 64 之间")
        if not nonce or len(nonce) > 128:
            raise ValueError("nonce 长度必须在 1 到 128 之间")
        if ttl_seconds <= 0:
            raise ValueError("ttl_seconds must be greater than zero")
        digest = hashlib.sha256(f"{scope}:{nonce}".encode("utf-8")).hexdigest()
        claimed = await self._redis.set(f"{self._key_prefix}:{digest}", "1", ex=ttl_seconds, nx=True)
        if not claimed:
            raise ReplayDetected("检测到重复 Nonce")
