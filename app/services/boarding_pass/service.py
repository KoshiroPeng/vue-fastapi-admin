from collections.abc import Callable

from app.services.auth_transaction import (
    AuthMethod,
    AuthStatus,
    AuthTransactionService,
    AuthTransactionStore,
)
from app.services.nce import NCEClient, NCEGuestCreateRequest

from .client import (
    BoardingPassAuthRequest,
    BoardingPassAuthResult,
    BoardingPassClient,
    BoardingPassRejected,
)


class BoardingPassAuthenticationService:
    def __init__(
        self,
        *,
        verifier: BoardingPassClient,
        nce: NCEClient,
        store: AuthTransactionStore,
        pii_hash_secret: str,
        transaction_ttl_seconds: int,
        guest_valid_minutes: int,
        id_factory: Callable[[], str] | None = None,
    ) -> None:
        self._verifier = verifier
        self._nce = nce
        self._store = store
        self._guest_valid_minutes = guest_valid_minutes
        self._transactions = AuthTransactionService(
            store,
            pii_hash_secret=pii_hash_secret,
            ttl_seconds=transaction_ttl_seconds,
            id_factory=id_factory,
        )

    async def authenticate(self, request: BoardingPassAuthRequest, trace_id: str) -> BoardingPassAuthResult:
        transaction = await self._transactions.start(
            auth_method=AuthMethod.BOARDING_PASS,
            client_ip=request.client_ip,
            client_mac=request.client_mac,
            ssid=request.ssid,
            trace_id=trace_id,
        )
        await self._store.transition(transaction.auth_tx_id, AuthStatus.PENDING)
        try:
            verification = await self._verifier.verify(request)
            if not verification.verified or verification.result_code != "0000":
                raise BoardingPassRejected("登机信息验证未通过")
            guest = await self._nce.create_guest(
                NCEGuestCreateRequest(
                    request_id=transaction.auth_tx_id,
                    username_prefix="bp",
                    valid_duration_minutes=self._guest_valid_minutes,
                    max_devices=1,
                    description="BoardingPass Three-Factor Verified",
                )
            )
        except Exception:
            await self._store.transition(transaction.auth_tx_id, AuthStatus.FAILED)
            raise
        await self._store.transition(transaction.auth_tx_id, AuthStatus.SUCCESS)
        return BoardingPassAuthResult(
            auth_tx_id=transaction.auth_tx_id,
            username=guest.username,
            password=guest.password,
            valid_until=guest.valid_until,
        )
