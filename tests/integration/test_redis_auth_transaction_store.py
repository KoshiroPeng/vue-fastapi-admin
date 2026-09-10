import os
from uuid import uuid4

import pytest
from redis.asyncio import Redis

from app.services.auth_transaction import (
    AuthStatus,
    AuthTransactionAlreadyConsumed,
    RedisAuthTransactionStore,
)
from tests.services.test_auth_transaction_store import build_transaction

pytestmark = pytest.mark.skipif(
    os.getenv("RUN_REDIS_INTEGRATION") != "1",
    reason="set RUN_REDIS_INTEGRATION=1 to test against an available Redis",
)


@pytest.mark.asyncio
async def test_real_redis_transaction_lifecycle_and_payload_safety() -> None:
    redis_url = os.getenv("REDIS_TEST_URL", "redis://127.0.0.1:16379/0")
    client = Redis.from_url(redis_url, decode_responses=True)
    key_prefix = f"test:wifi:auth:tx:{uuid4().hex}"
    store = RedisAuthTransactionStore(client, key_prefix=key_prefix)
    transaction = build_transaction()
    key = f"{key_prefix}:{transaction.auth_tx_id}"

    try:
        assert await client.ping() is True
        await store.create(transaction, ttl_seconds=300)
        pending = await store.transition(transaction.auth_tx_id, AuthStatus.PENDING)
        successful = await store.transition(transaction.auth_tx_id, AuthStatus.SUCCESS)
        consumed = await store.consume(transaction.auth_tx_id)
        raw_payload = await client.get(key)
        ttl = await client.ttl(key)

        assert pending.status is AuthStatus.PENDING
        assert successful.status is AuthStatus.SUCCESS
        assert consumed.consumed_at is not None
        assert raw_payload is not None
        assert "client_ip_hash" in raw_payload
        assert "client_mac_hash" in raw_payload
        assert "password" not in raw_payload.lower()
        assert 0 < ttl <= 300
        with pytest.raises(AuthTransactionAlreadyConsumed):
            await store.consume(transaction.auth_tx_id)
    finally:
        await client.delete(key)
        await client.aclose()
