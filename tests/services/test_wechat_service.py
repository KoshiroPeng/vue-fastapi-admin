import pytest

from app.services.auth_transaction import AuthStatus, InMemoryAuthTransactionStore
from app.services.wechat import WeChatAuthService, build_wechat_signature


@pytest.mark.asyncio
async def test_wechat_callback_requires_nce_success_and_updates_transaction() -> None:
    store = InMemoryAuthTransactionStore()
    service = WeChatAuthService(
        store=store,
        pii_hash_secret="test-pii-secret",
        callback_secret="test-callback-secret",
        transaction_ttl_seconds=300,
        id_factory=lambda: "tx_wechat_001",
    )
    transaction = await service.start(
        client_ip="10.1.2.3",
        client_mac="AA-BB-CC-DD-EE-FF",
        ssid="Airport-Free-WiFi",
        trace_id="trace-wechat",
    )
    body = b'{"authTxId":"tx_wechat_001","result":"SUCCESS","nceSuccess":true}'
    signature = build_wechat_signature("test-callback-secret", "1789027200", "nonce-001", body)

    await service.apply_callback(
        auth_tx_id=transaction.auth_tx_id,
        result="SUCCESS",
        nce_success=True,
        timestamp="1789027200",
        nonce="nonce-001",
        body=body,
        signature=signature,
    )

    assert (await service.status("tx_wechat_001")).status is AuthStatus.SUCCESS


@pytest.mark.asyncio
async def test_wechat_callback_cannot_claim_success_without_nce_proof() -> None:
    store = InMemoryAuthTransactionStore()
    service = WeChatAuthService(
        store=store,
        pii_hash_secret="test-pii-secret",
        callback_secret="test-callback-secret",
        transaction_ttl_seconds=300,
        id_factory=lambda: "tx_wechat_002",
    )
    transaction = await service.start(
        client_ip="10.1.2.3",
        client_mac="AA-BB-CC-DD-EE-FF",
        ssid=None,
        trace_id="trace-wechat",
    )
    body = b"callback"
    signature = build_wechat_signature("test-callback-secret", "1789027200", "nonce-002", body)

    await service.apply_callback(
        auth_tx_id=transaction.auth_tx_id,
        result="SUCCESS",
        nce_success=False,
        timestamp="1789027200",
        nonce="nonce-002",
        body=body,
        signature=signature,
    )

    assert (await service.status("tx_wechat_002")).status is AuthStatus.FAILED
