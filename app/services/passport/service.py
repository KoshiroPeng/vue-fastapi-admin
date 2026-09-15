from collections.abc import Callable

from app.services.auth_transaction import AuthMethod, AuthStatus, AuthTransactionService, AuthTransactionStore
from app.services.nce import (
    NCEClient,
    NCEGuestCreateRequest,
    NCETerminalAuthorizationRequest,
    authorize_terminal_and_wait,
)

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
        haca_policy_name: str | None = None,
        haca_poll_attempts: int = 10,
        haca_poll_interval_ms: int = 1000,
        id_factory: Callable[[], str] | None = None,
    ) -> None:
        self._ocr = ocr
        self._nce = nce
        self._store = store
        self._guest_valid_minutes = guest_valid_minutes
        self._haca_policy_name = haca_policy_name
        self._haca_poll_attempts = haca_poll_attempts
        self._haca_poll_interval_ms = haca_poll_interval_ms
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
        device_mac: str | None,
        device_esn: str | None,
        ap_mac: str | None,
        node_ip: str | None,
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
                    terminal_mac=client_mac,
                )
            )
            authorization = await authorize_terminal_and_wait(
                self._nce,
                NCETerminalAuthorizationRequest(
                    request_id=transaction.auth_tx_id,
                    username=guest.username,
                    client_ip=client_ip,
                    client_mac=client_mac,
                    ssid=ssid or "Airport-Free-WiFi",
                    device_mac=device_mac,
                    device_esn=device_esn,
                    ap_mac=ap_mac,
                    node_ip=node_ip,
                    policy_name=self._haca_policy_name,
                    permit_seconds=self._guest_valid_minutes * 60,
                ),
                poll_attempts=self._haca_poll_attempts,
                poll_interval_ms=self._haca_poll_interval_ms,
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
            authorization_session_id=authorization.session_id,
        )
