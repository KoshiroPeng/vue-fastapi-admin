import asyncio
import time
from collections.abc import Callable
from datetime import datetime, timezone

from .errors import (
    AuthTransactionAlreadyConsumed,
    AuthTransactionNotConsumable,
    AuthTransactionNotFound,
    InvalidAuthStatusTransition,
)
from .models import AuthStatus, AuthTransaction, is_transition_allowed


class InMemoryAuthTransactionStore:
    """Process-local transaction store used by fast unit tests."""

    def __init__(
        self,
        monotonic: Callable[[], float] | None = None,
        clock: Callable[[], datetime] | None = None,
    ) -> None:
        self._monotonic = monotonic or time.monotonic
        self._clock = clock or (lambda: datetime.now(timezone.utc))
        self._items: dict[str, tuple[float, AuthTransaction]] = {}
        self._lock = asyncio.Lock()

    async def create(self, transaction: AuthTransaction, ttl_seconds: int) -> None:
        if ttl_seconds <= 0:
            raise ValueError("ttl_seconds must be greater than zero")
        async with self._lock:
            self._items[transaction.auth_tx_id] = (self._monotonic() + ttl_seconds, transaction)

    async def get(self, auth_tx_id: str) -> AuthTransaction | None:
        async with self._lock:
            return self._get_active(auth_tx_id)

    async def transition(self, auth_tx_id: str, target: AuthStatus) -> AuthTransaction:
        async with self._lock:
            transaction = self._get_active(auth_tx_id)
            if transaction is None:
                raise AuthTransactionNotFound(auth_tx_id)
            if not is_transition_allowed(transaction.status, target):
                raise InvalidAuthStatusTransition(transaction.status, target)
            updated = transaction.model_copy(update={"status": target})
            expires_at, _ = self._items[auth_tx_id]
            self._items[auth_tx_id] = (expires_at, updated)
            return updated

    async def consume(self, auth_tx_id: str) -> AuthTransaction:
        async with self._lock:
            transaction = self._get_active(auth_tx_id)
            if transaction is None:
                raise AuthTransactionNotFound(auth_tx_id)
            if transaction.status is not AuthStatus.SUCCESS:
                raise AuthTransactionNotConsumable(auth_tx_id)
            if transaction.consumed_at is not None:
                raise AuthTransactionAlreadyConsumed(auth_tx_id)
            updated = transaction.model_copy(update={"consumed_at": self._clock()})
            expires_at, _ = self._items[auth_tx_id]
            self._items[auth_tx_id] = (expires_at, updated)
            return updated

    def _get_active(self, auth_tx_id: str) -> AuthTransaction | None:
        item = self._items.get(auth_tx_id)
        if item is None:
            return None
        expires_at, transaction = item
        if expires_at <= self._monotonic():
            self._items.pop(auth_tx_id, None)
            return None
        return transaction
