from datetime import date, datetime, timezone

import pytest

from app.services.auth_transaction import AuthStatus, InMemoryAuthTransactionStore
from app.services.boarding_pass import (
    BoardingPassAuthRequest,
    BoardingPassAuthenticationService,
    BoardingPassRejected,
    MockBoardingPassClient,
)
from app.services.nce.mock import MockNCEClient


@pytest.mark.asyncio
async def test_boarding_pass_mock_creates_nce_guest_and_success_transaction() -> None:
    store = InMemoryAuthTransactionStore()
    service = BoardingPassAuthenticationService(
        verifier=MockBoardingPassClient(),
        nce=MockNCEClient(clock=lambda: datetime(2026, 9, 10, 8, 0, tzinfo=timezone.utc)),
        store=store,
        pii_hash_secret="test-pii-secret",
        transaction_ttl_seconds=300,
        guest_valid_minutes=480,
        haca_poll_interval_ms=0,
        id_factory=lambda: "tx_boarding_001",
    )

    result = await service.authenticate(
        BoardingPassAuthRequest(
            flight_date=date(2026, 9, 10),
            flight_no="CA1234",
            seat_no="16A",
            document_last4="5678",
            client_ip="10.1.2.3",
            client_mac="AA-BB-CC-DD-EE-FF",
            ssid="Airport-Free-WiFi",
            device_mac="11-22-33-44-55-66",
        ),
        trace_id="trace-001",
    )

    assert result.auth_tx_id == "tx_boarding_001"
    assert result.username.startswith("bp_")
    assert result.authorization_session_id
    assert (await store.get("tx_boarding_001")).status is AuthStatus.SUCCESS


@pytest.mark.asyncio
async def test_boarding_pass_rejection_does_not_create_success() -> None:
    store = InMemoryAuthTransactionStore()
    service = BoardingPassAuthenticationService(
        verifier=MockBoardingPassClient(),
        nce=MockNCEClient(),
        store=store,
        pii_hash_secret="test-pii-secret",
        transaction_ttl_seconds=300,
        guest_valid_minutes=480,
        haca_poll_interval_ms=0,
        id_factory=lambda: "tx_boarding_002",
    )

    with pytest.raises(BoardingPassRejected):
        await service.authenticate(
            BoardingPassAuthRequest(
                flight_date=date(2026, 9, 10),
                flight_no="CA9999",
                seat_no="99Z",
                document_last4="0000",
                client_ip="10.1.2.3",
                client_mac="AA-BB-CC-DD-EE-FF",
                device_mac="11-22-33-44-55-66",
            ),
            trace_id="trace-002",
        )
    assert (await store.get("tx_boarding_002")).status is AuthStatus.FAILED
