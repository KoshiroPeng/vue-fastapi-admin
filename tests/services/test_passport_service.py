from datetime import datetime, timezone

import pytest

from app.services.auth_transaction import AuthStatus, InMemoryAuthTransactionStore
from app.services.nce.mock import MockNCEClient
from app.services.passport import MockPassportOCRClient, PassportAuthenticationService, PassportImage


@pytest.mark.asyncio
async def test_passport_mock_ocr_creates_guest_without_persisting_image() -> None:
    store = InMemoryAuthTransactionStore()
    service = PassportAuthenticationService(
        ocr=MockPassportOCRClient(),
        nce=MockNCEClient(clock=lambda: datetime(2026, 9, 10, 8, 0, tzinfo=timezone.utc)),
        store=store,
        pii_hash_secret="test-pii-secret",
        transaction_ttl_seconds=300,
        guest_valid_minutes=480,
        haca_poll_interval_ms=0,
        id_factory=lambda: "tx_passport_001",
    )
    image_bytes = b"\xff\xd8\xff" + b"mock-passport-image"

    result = await service.authenticate(
        image=PassportImage(content=image_bytes, content_type="image/jpeg"),
        client_ip="10.1.2.3",
        client_mac="AA-BB-CC-DD-EE-FF",
        ssid="Airport-Free-WiFi",
        device_mac="11-22-33-44-55-66",
        device_esn=None,
        ap_mac=None,
        node_ip=None,
        trace_id="trace-passport",
    )

    assert result.username.startswith("pass_")
    assert result.passport_number_masked == "E****1234"
    assert result.authorization_session_id
    assert (await store.get("tx_passport_001")).status is AuthStatus.SUCCESS
    assert "mock-passport-image" not in (await store.get("tx_passport_001")).model_dump_json()
