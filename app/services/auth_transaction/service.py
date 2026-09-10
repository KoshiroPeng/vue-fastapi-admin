from collections.abc import Callable
from datetime import datetime, timedelta, timezone
from uuid import uuid4

from app.core.masking import hash_ip, hash_mac

from .models import AuthMethod, AuthStatus, AuthTransaction
from .store import AuthTransactionStore


class AuthTransactionService:
    def __init__(
        self,
        store: AuthTransactionStore,
        pii_hash_secret: str,
        ttl_seconds: int,
        clock: Callable[[], datetime] | None = None,
        id_factory: Callable[[], str] | None = None,
    ) -> None:
        if not pii_hash_secret:
            raise ValueError("PII_HASH_SECRET 尚未配置")
        self._store = store
        self._pii_hash_secret = pii_hash_secret
        self._ttl_seconds = ttl_seconds
        self._clock = clock or (lambda: datetime.now(timezone.utc))
        self._id_factory = id_factory or (lambda: f"tx_{uuid4().hex}")

    async def start(
        self,
        *,
        auth_method: AuthMethod,
        client_ip: str,
        client_mac: str,
        ssid: str | None,
        trace_id: str,
    ) -> AuthTransaction:
        now = self._clock()
        transaction = AuthTransaction(
            auth_tx_id=self._id_factory(),
            auth_method=auth_method,
            status=AuthStatus.INIT,
            client_ip_hash=hash_ip(client_ip, self._pii_hash_secret),
            client_mac_hash=hash_mac(client_mac, self._pii_hash_secret),
            ssid=ssid,
            expire_at=now + timedelta(seconds=self._ttl_seconds),
            trace_id=trace_id,
        )
        await self._store.create(transaction, self._ttl_seconds)
        return transaction
