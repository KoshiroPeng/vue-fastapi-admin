from typing import Protocol

from .models import AuthStatus, AuthTransaction


class AuthTransactionStore(Protocol):
    async def create(self, transaction: AuthTransaction, ttl_seconds: int) -> None:
        """Persist a new transaction for a bounded lifetime."""

    async def get(self, auth_tx_id: str) -> AuthTransaction | None:
        """Return an active transaction, or None when absent/expired."""

    async def transition(self, auth_tx_id: str, target: AuthStatus) -> AuthTransaction:
        """Atomically move a transaction to an allowed target state."""

    async def consume(self, auth_tx_id: str) -> AuthTransaction:
        """Atomically consume one successful transaction exactly once."""
