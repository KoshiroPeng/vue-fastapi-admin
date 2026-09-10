from datetime import datetime, timedelta, timezone

from .client import BoardingPassAuthRequest, BoardingPassVerification


class MockBoardingPassClient:
    async def verify(self, request: BoardingPassAuthRequest) -> BoardingPassVerification:
        verified = (
            request.flight_date.isoformat() == "2026-09-10"
            and request.flight_no == "CA1234"
            and request.seat_no == "16A"
            and request.document_last4 == "5678"
        )
        return BoardingPassVerification(
            verified=verified,
            result_code="0000" if verified else "1001",
            valid_until=datetime.now(timezone.utc) + timedelta(hours=8) if verified else None,
        )
