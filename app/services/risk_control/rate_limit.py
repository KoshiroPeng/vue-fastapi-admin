import re
import time
from uuid import uuid4

from pydantic import BaseModel, ConfigDict, Field
from redis.asyncio import Redis

from .errors import RateLimitExceeded

_HASH_PATTERN = re.compile(r"^[0-9a-f]{64}$")
_RATE_LIMIT_SCRIPT = """
local key = KEYS[1]
local now_ms = tonumber(ARGV[1])
local window_ms = tonumber(ARGV[2])
local limit = tonumber(ARGV[3])
local member = ARGV[4]
local ttl_seconds = tonumber(ARGV[5])
local cutoff = now_ms - window_ms

redis.call('ZREMRANGEBYSCORE', key, '-inf', cutoff)
local count = redis.call('ZCARD', key)
if count >= limit then
    local oldest = redis.call('ZRANGE', key, 0, 0, 'WITHSCORES')
    local retry_after = math.ceil((tonumber(oldest[2]) + window_ms - now_ms) / 1000)
    if retry_after < 1 then retry_after = 1 end
    redis.call('EXPIRE', key, ttl_seconds)
    return {0, 0, retry_after}
end

redis.call('ZADD', key, now_ms, member)
redis.call('EXPIRE', key, ttl_seconds)
return {1, limit - count - 1, 0}
"""


class RateLimitDecision(BaseModel):
    model_config = ConfigDict(frozen=True)

    remaining: int = Field(ge=0)


class RedisSlidingWindowRateLimiter:
    def __init__(self, redis: Redis, key_prefix: str = "wifi:rate") -> None:
        self._redis = redis
        self._key_prefix = key_prefix.rstrip(":")

    async def check(
        self,
        scope: str,
        subject_hash: str,
        limit: int,
        window_seconds: int,
        now_ms: int | None = None,
    ) -> RateLimitDecision:
        if not scope or len(scope) > 64:
            raise ValueError("scope 长度必须在 1 到 64 之间")
        if not _HASH_PATTERN.fullmatch(subject_hash):
            raise ValueError("subject_hash 必须是 64 位小写十六进制摘要")
        if limit <= 0 or window_seconds <= 0:
            raise ValueError("limit and window_seconds must be greater than zero")

        effective_now_ms = now_ms if now_ms is not None else int(time.time() * 1000)
        key = f"{self._key_prefix}:{scope}:{subject_hash}"
        result = await self._redis.eval(
            _RATE_LIMIT_SCRIPT,
            1,
            key,
            effective_now_ms,
            window_seconds * 1000,
            limit,
            f"{effective_now_ms}:{uuid4().hex}",
            window_seconds + 1,
        )
        allowed, remaining, retry_after = (int(value) for value in result)
        if not allowed:
            raise RateLimitExceeded(retry_after)
        return RateLimitDecision(remaining=remaining)
