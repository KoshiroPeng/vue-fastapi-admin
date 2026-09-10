from datetime import datetime, timedelta, timezone

import pytest

from app.services.auth_transaction import (
    AuthMethod,
    AuthStatus,
    AuthTransaction,
    InMemoryAuthTransactionStore,
    AuthTransactionAlreadyConsumed,
    AuthTransactionNotConsumable,
    InvalidAuthStatusTransition,
)


def build_transaction() -> AuthTransaction:
    now = datetime(2026, 9, 10, 8, 0, tzinfo=timezone.utc)
    return AuthTransaction(
        auth_tx_id="tx_test_001",
        auth_method=AuthMethod.KIOSK,
        status=AuthStatus.INIT,
        client_ip_hash="a" * 64,
        client_mac_hash="b" * 64,
        ssid="Airport-Free-WiFi",
        expire_at=now + timedelta(minutes=5),
        trace_id="trace_test_001",
    )


@pytest.mark.asyncio
async def test_memory_store_round_trips_short_lived_transaction() -> None:
    store = InMemoryAuthTransactionStore()
    transaction = build_transaction()

    await store.create(transaction, ttl_seconds=300)

    assert await store.get(transaction.auth_tx_id) == transaction


@pytest.mark.asyncio
async def test_memory_store_discards_expired_transaction() -> None:
    current = 100.0
    store = InMemoryAuthTransactionStore(monotonic=lambda: current)
    transaction = build_transaction()
    await store.create(transaction, ttl_seconds=1)

    current = 101.0

    assert await store.get(transaction.auth_tx_id) is None


@pytest.mark.asyncio
async def test_transaction_allows_only_declared_status_transitions() -> None:
    store = InMemoryAuthTransactionStore()
    transaction = build_transaction()
    await store.create(transaction, ttl_seconds=300)

    pending = await store.transition(transaction.auth_tx_id, AuthStatus.PENDING)
    successful = await store.transition(transaction.auth_tx_id, AuthStatus.SUCCESS)

    assert pending.status is AuthStatus.PENDING
    assert successful.status is AuthStatus.SUCCESS

    with pytest.raises(InvalidAuthStatusTransition):
        await store.transition(transaction.auth_tx_id, AuthStatus.FAILED)


@pytest.mark.asyncio
async def test_successful_transaction_can_be_consumed_only_once() -> None:
    consumed_at = datetime(2026, 9, 10, 8, 1, tzinfo=timezone.utc)
    store = InMemoryAuthTransactionStore(clock=lambda: consumed_at)
    transaction = build_transaction()
    await store.create(transaction, ttl_seconds=300)

    with pytest.raises(AuthTransactionNotConsumable):
        await store.consume(transaction.auth_tx_id)

    await store.transition(transaction.auth_tx_id, AuthStatus.PENDING)
    await store.transition(transaction.auth_tx_id, AuthStatus.SUCCESS)
    consumed = await store.consume(transaction.auth_tx_id)

    assert consumed.consumed_at == consumed_at
    with pytest.raises(AuthTransactionAlreadyConsumed):
        await store.consume(transaction.auth_tx_id)
