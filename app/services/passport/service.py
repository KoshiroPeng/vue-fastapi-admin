from collections.abc import Callable

from app.services.auth_transaction import AuthMethod, AuthStatus, AuthTransactionService, AuthTransactionStore
from app.services.nce import NCEClient, NCEGuestCreateRequest

from .client import PassportAuthResult, PassportImage, PassportOCRClient, PassportOCRRejected


class PassportAuthenticationService:
    def __init__(
        self,
        *,
        ocr: PassportOCRClient,
        nce: NCEClient,
        store: AuthTransactionStore,
        pii_hash_secret: str,
        transaction_ttl_seconds: int,
        guest_valid_minutes: int,
        id_factory: Callable[[], str] | None = None,
    ) -> None:
        self._ocr = ocr
        self._nce = nce
        self._store = store
        self._guest_valid_minutes = guest_valid_minutes
        self._transactions = AuthTransactionService(
            store,
            pii_hash_secret=pii_hash_secret,
            ttl_seconds=transaction_ttl_seconds,
            id_factory=id_factory,
        )

    async def authenticate(
        self,
        *,
        image: PassportImage,
        client_ip: str,
        client_mac: str,
        ssid: str | None,
        trace_id: str,
    ) -> PassportAuthResult:
        transaction = await self._transactions.start(
            auth_method=AuthMethod.PASSPORT,
            client_ip=client_ip,
            client_mac=client_mac,
            ssid=ssid,
            trace_id=trace_id,
        )
        await self._store.transition(transaction.auth_tx_id, AuthStatus.PENDING)
        try:
            recognized = await self._ocr.recognize(image)
            if not recognized.mrz_valid or recognized.result_code != "0":
                raise PassportOCRRejected("护照识别或 MRZ 校验未通过")
            guest = await self._nce.create_guest(
                NCEGuestCreateRequest(
                    request_id=transaction.auth_tx_id,
                    username_prefix="pass",
                    valid_duration_minutes=self._guest_valid_minutes,
                    max_devices=1,
                    description="Passport OCR Verified",
                )
            )
        except Exception:
            await self._store.transition(transaction.auth_tx_id, AuthStatus.FAILED)
            raise
        await self._store.transition(transaction.auth_tx_id, AuthStatus.SUCCESS)
        passport_number = recognized.passport_number.get_secret_value()
        masked = f"{passport_number[:1]}****{passport_number[-4:]}"
        return PassportAuthResult(
            auth_tx_id=transaction.auth_tx_id,
            username=guest.username,
            password=guest.password,
            passport_number_masked=masked,
            valid_until=guest.valid_until,
        )
