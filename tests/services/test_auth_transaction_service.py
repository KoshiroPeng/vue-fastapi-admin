from datetime import datetime, timezone

import pytest

from app.services.auth_transaction import AuthMethod, InMemoryAuthTransactionStore
from app.services.auth_transaction.service import AuthTransactionService


@pytest.mark.asyncio
async def test_auth_transaction_service_stores_only_hashed_identifiers() -> None:
    store = InMemoryAuthTransactionStore()
    service = AuthTransactionService(
        store,
        pii_hash_secret="test-pii-secret",
        ttl_seconds=300,
        clock=lambda: datetime(2026, 9, 10, 8, 0, tzinfo=timezone.utc),
        id_factory=lambda: "tx_test_001",
    )

    transaction = await service.start(
        auth_method=AuthMethod.BOARDING_PASS,
        client_ip="10.1.2.3",
        client_mac="AA-BB-CC-DD-EE-FF",
        ssid="Airport-Free-WiFi",
        trace_id="trace-001",
    )

    assert transaction.auth_tx_id == "tx_test_001"
    assert transaction.client_ip_hash != "10.1.2.3"
    assert transaction.client_mac_hash != "AA-BB-CC-DD-EE-FF"
    assert len(transaction.client_ip_hash) == 64
    assert await store.get("tx_test_001") == transaction
