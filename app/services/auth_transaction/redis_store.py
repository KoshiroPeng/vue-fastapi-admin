from collections.abc import Callable
from datetime import datetime, timezone

from redis.asyncio import Redis
from redis.exceptions import WatchError

from .errors import (
    AuthTransactionAlreadyConsumed,
    AuthTransactionNotConsumable,
    AuthTransactionNotFound,
    InvalidAuthStatusTransition,
)
from .models import AuthStatus, AuthTransaction, is_transition_allowed


class RedisAuthTransactionStore:
    """Redis-backed transaction store with optimistic atomic updates."""

    def __init__(
        self,
        redis: Redis,
        key_prefix: str = "wifi:auth:tx",
        clock: Callable[[], datetime] | None = None,
    ) -> None:
        self._redis = redis
        self._key_prefix = key_prefix.rstrip(":")
        self._clock = clock or (lambda: datetime.now(timezone.utc))

    async def create(self, transaction: AuthTransaction, ttl_seconds: int) -> None:
        if ttl_seconds <= 0:
            raise ValueError("ttl_seconds must be greater than zero")
        created = await self._redis.set(
            self._key(transaction.auth_tx_id),
            transaction.model_dump_json(),
            ex=ttl_seconds,
            nx=True,
        )
        if not created:
            raise ValueError("authentication transaction already exists")

    async def get(self, auth_tx_id: str) -> AuthTransaction | None:
        raw = await self._redis.get(self._key(auth_tx_id))
        return self._deserialize(raw) if raw is not None else None

    async def transition(self, auth_tx_id: str, target: AuthStatus) -> AuthTransaction:
        def update(transaction: AuthTransaction) -> AuthTransaction:
            if not is_transition_allowed(transaction.status, target):
                raise InvalidAuthStatusTransition(transaction.status, target)
            return transaction.model_copy(update={"status": target})

        return await self._atomic_update(auth_tx_id, update)

    async def consume(self, auth_tx_id: str) -> AuthTransaction:
        def update(transaction: AuthTransaction) -> AuthTransaction:
            if transaction.status is not AuthStatus.SUCCESS:
                raise AuthTransactionNotConsumable(auth_tx_id)
            if transaction.consumed_at is not None:
                raise AuthTransactionAlreadyConsumed(auth_tx_id)
            return transaction.model_copy(update={"consumed_at": self._clock()})

        return await self._atomic_update(auth_tx_id, update)

    async def _atomic_update(
        self,
        auth_tx_id: str,
        update: Callable[[AuthTransaction], AuthTransaction],
    ) -> AuthTransaction:
        key = self._key(auth_tx_id)
        while True:
            async with self._redis.pipeline(transaction=True) as pipeline:
                try:
                    await pipeline.watch(key)
                    raw = await pipeline.get(key)
                    if raw is None:
                        raise AuthTransactionNotFound(auth_tx_id)
                    ttl_ms = await pipeline.pttl(key)
                    if ttl_ms <= 0:
                        raise AuthTransactionNotFound(auth_tx_id)
                    updated = update(self._deserialize(raw))
                    pipeline.multi()
                    pipeline.set(key, updated.model_dump_json(), px=ttl_ms)
                    await pipeline.execute()
                    return updated
                except WatchError:
                    continue

    def _key(self, auth_tx_id: str) -> str:
        return f"{self._key_prefix}:{auth_tx_id}"

    @staticmethod
    def _deserialize(raw: str | bytes) -> AuthTransaction:
        return AuthTransaction.model_validate_json(raw)
