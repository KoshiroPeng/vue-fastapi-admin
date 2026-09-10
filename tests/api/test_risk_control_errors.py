import httpx
import pytest
from fastapi import FastAPI
from fastapi.exceptions import RequestValidationError

from app.core.exceptions import RequestValidationHandle, RiskControlHandle
from app.schemas.kiosk import KioskCreateGuestRequest
from app.services.risk_control import RateLimitExceeded, ReplayDetected, RiskControlError


@pytest.mark.asyncio
async def test_rate_limit_error_returns_429_and_retry_after() -> None:
    app = FastAPI()
    app.add_exception_handler(RiskControlError, RiskControlHandle)

    @app.get("/limited")
    async def limited() -> None:
        raise RateLimitExceeded(retry_after_seconds=42)

    async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://test") as client:
        response = await client.get("/limited")

    assert response.status_code == 429
    assert response.headers["Retry-After"] == "42"
    assert response.json() == {
        "code": 429,
        "msg": "操作过于频繁，请稍后再试",
        "data": None,
        "error_code": "RATE_LIMITED",
    }


@pytest.mark.asyncio
async def test_replay_error_returns_conflict_without_internal_details() -> None:
    app = FastAPI()
    app.add_exception_handler(RiskControlError, RiskControlHandle)

    @app.post("/callback")
    async def callback() -> None:
        raise ReplayDetected("raw nonce is duplicated")

    async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://test") as client:
        response = await client.post("/callback")

    assert response.status_code == 409
    assert response.json()["error_code"] == "REPLAY_DETECTED"
    assert "raw nonce" not in response.text


@pytest.mark.asyncio
async def test_validation_error_does_not_echo_sensitive_input() -> None:
    app = FastAPI()
    app.add_exception_handler(RequestValidationError, RequestValidationHandle)

    @app.post("/kiosk")
    async def kiosk(_: KioskCreateGuestRequest) -> None:
        return None

    sensitive_invalid_digest = "traveler-document-value"
    async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://test") as client:
        response = await client.post(
            "/kiosk",
            json={"idType": "ID_CARD", "idDigest": sensitive_invalid_digest},
        )

    assert response.status_code == 422
    assert sensitive_invalid_digest not in response.text
    assert response.json()["error_code"] == "REQUEST_INVALID"
