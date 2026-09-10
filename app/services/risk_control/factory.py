from app.core.redis import redis_manager

from .idempotency import RedisIdempotencyGuard
from .rate_limit import RedisSlidingWindowRateLimiter
from .replay import RedisReplayProtector


def get_replay_protector() -> RedisReplayProtector:
    return RedisReplayProtector(redis_manager.client)


def get_rate_limiter() -> RedisSlidingWindowRateLimiter:
    return RedisSlidingWindowRateLimiter(redis_manager.client)


def get_idempotency_guard() -> RedisIdempotencyGuard:
    return RedisIdempotencyGuard(redis_manager.client)
