from redis.asyncio import Redis

from app.log import logger
from app.settings import settings


class RedisConnectionManager:
    def __init__(self, redis_url: str) -> None:
        self._redis_url = redis_url
        self._client: Redis | None = None

    @property
    def client(self) -> Redis:
        if self._client is None:
            raise RuntimeError("Redis 尚未连接")
        return self._client

    async def connect(self) -> None:
        if self._client is not None:
            return
        client = Redis.from_url(self._redis_url, encoding="utf-8", decode_responses=True)
        try:
            await client.ping()
        except Exception:
            await client.aclose()
            logger.exception("event=redis_connect_failed")
            raise
        self._client = client
        logger.info("event=redis_connected")

    async def close(self) -> None:
        client = self._client
        self._client = None
        if client is None:
            return
        await client.aclose()
        logger.info("event=redis_closed")


redis_manager = RedisConnectionManager(settings.REDIS_URL)
