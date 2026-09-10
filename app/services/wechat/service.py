import hashlib
import hmac
from collections.abc import Callable

from app.services.auth_transaction import (
    AuthMethod,
    AuthStatus,
    AuthTransaction,
    AuthTransactionService,
    AuthTransactionStore,
)


class WeChatCallbackRejected(Exception):
    pass


def build_wechat_signature(secret: str, timestamp: str, nonce: str, body: bytes) -> str:
    body_digest = hashlib.sha256(body).hexdigest()
    canonical = f"{timestamp}\n{nonce}\n{body_digest}".encode("utf-8")
    return hmac.new(secret.encode("utf-8"), canonical, hashlib.sha256).hexdigest()


class WeChatAuthService:
    def __init__(
        self,
        *,
        store: AuthTransactionStore,
        pii_hash_secret: str,
        callback_secret: str,
        transaction_ttl_seconds: int,
        id_factory: Callable[[], str] | None = None,
    ) -> None:
        if not callback_secret:
            raise ValueError("WECHAT_CALLBACK_SECRET 尚未配置")
        self._store = store
        self._callback_secret = callback_secret
        self._transactions = AuthTransactionService(
            store,
            pii_hash_secret=pii_hash_secret,
            ttl_seconds=transaction_ttl_seconds,
            id_factory=id_factory,
        )

    async def start(
        self,
        *,
        client_ip: str,
        client_mac: str,
        ssid: str | None,
        trace_id: str,
    ) -> AuthTransaction:
        transaction = await self._transactions.start(
            auth_method=AuthMethod.WECHAT,
            client_ip=client_ip,
            client_mac=client_mac,
            ssid=ssid,
            trace_id=trace_id,
        )
        return await self._store.transition(transaction.auth_tx_id, AuthStatus.PENDING)

    async def apply_callback(
        self,
        *,
        auth_tx_id: str,
        result: str,
        nce_success: bool,
        timestamp: str,
        nonce: str,
        body: bytes,
        signature: str,
    ) -> AuthTransaction:
        expected = build_wechat_signature(self._callback_secret, timestamp, nonce, body)
        if not hmac.compare_digest(signature.lower(), expected):
            raise WeChatCallbackRejected("微信状态回写签名无效")
        target = AuthStatus.SUCCESS if result == "SUCCESS" and nce_success else AuthStatus.FAILED
        return await self._store.transition(auth_tx_id, target)

    async def mock_complete(self, auth_tx_id: str) -> AuthTransaction:
        return await self._store.transition(auth_tx_id, AuthStatus.SUCCESS)

    async def status(self, auth_tx_id: str) -> AuthTransaction | None:
        return await self._store.get(auth_tx_id)
