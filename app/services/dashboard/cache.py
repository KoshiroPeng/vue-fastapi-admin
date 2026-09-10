import asyncio
import hashlib
import json
import re
import weakref
from collections.abc import Awaitable, Callable
from typing import TypeVar

from pydantic import BaseModel, ValidationError
from redis.asyncio import Redis
from redis.exceptions import RedisError

from app.core.request_context import get_request_id
from app.log import logger

T = TypeVar("T", bound=BaseModel)
_NAMESPACE_PATTERN = re.compile(r"^[a-z][a-z0-9-]{0,63}$")


class RedisQueryCache:
    """Short-lived shared cache with per-process single-flight loading."""

    def __init__(self, redis: Redis, key_prefix: str = "wifi:dashboard:cache") -> None:
        self._redis = redis
        self._key_prefix = key_prefix.rstrip(":")
        self._locks: weakref.WeakValueDictionary[str, asyncio.Lock] = weakref.WeakValueDictionary()

    async def get_or_load(
        self,
        *,
        namespace: str,
        key_data: dict,
        ttl_seconds: int,
        model: type[T],
        loader: Callable[[], Awaitable[T]],
    ) -> T:
        if not _NAMESPACE_PATTERN.fullmatch(namespace):
            raise ValueError("cache namespace 格式无效")
        if ttl_seconds <= 0:
            raise ValueError("ttl_seconds must be greater than zero")
        key = self._key(namespace, key_data)
        cached = await self._get(key, model)
        if cached is not None:
            return cached

        lock = self._locks.setdefault(key, asyncio.Lock())
        async with lock:
            cached = await self._get(key, model)
            if cached is not None:
                return cached
            loaded = await loader()
            try:
                await self._redis.set(key, loaded.model_dump_json(), ex=ttl_seconds)
            except RedisError:
                logger.warning(
                    "event=dashboard_cache_write_failed request_id={} namespace={}",
                    get_request_id() or "-",
                    namespace,
                )
            return loaded

    async def _get(self, key: str, model: type[T]) -> T | None:
        try:
            raw = await self._redis.get(key)
        except RedisError:
            logger.warning("event=dashboard_cache_read_failed request_id={}", get_request_id() or "-")
            return None
        if raw is None:
            return None
        try:
            return model.model_validate_json(raw)
        except (ValidationError, ValueError):
            logger.warning("event=dashboard_cache_invalid request_id={}", get_request_id() or "-")
            try:
                await self._redis.delete(key)
            except RedisError:
                logger.warning("event=dashboard_cache_delete_failed request_id={}", get_request_id() or "-")
            return None

    def _key(self, namespace: str, key_data: dict) -> str:
        canonical = json.dumps(key_data, ensure_ascii=False, sort_keys=True, separators=(",", ":"), default=str)
        digest = hashlib.sha256(canonical.encode("utf-8")).hexdigest()
        return f"{self._key_prefix}:{namespace}:{digest}"
