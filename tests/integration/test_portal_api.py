import json
import os
import time
from uuid import uuid4

import httpx
import pytest
from fastapi import FastAPI, HTTPException
from redis.asyncio import Redis

from app.api.v1.portal import portal_router
from app.core.exceptions import HttpExcHandle, RiskControlHandle
from app.services.auth_transaction import RedisAuthTransactionStore
from app.services.boarding_pass import BoardingPassAuthenticationService, MockBoardingPassClient
from app.services.nce.mock import MockNCEClient
from app.services.passport import MockPassportOCRClient, PassportAuthenticationService
from app.services.portal_factory import get_boarding_pass_service, get_passport_service, get_wechat_service
from app.services.risk_control import (
    RedisReplayProtector,
    RedisSlidingWindowRateLimiter,
    RiskControlError,
    get_rate_limiter,
    get_replay_protector,
)
from app.services.wechat import WeChatAuthService, build_wechat_signature
from app.settings import settings

pytestmark = pytest.mark.skipif(
    os.getenv("RUN_REDIS_INTEGRATION") != "1",
    reason="set RUN_REDIS_INTEGRATION=1 to test against an available Redis",
)


@pytest.mark.asyncio
async def test_mock_portal_backend_supports_boarding_pass_passport_and_wechat(monkeypatch: pytest.MonkeyPatch) -> None:
    redis_url = os.getenv("REDIS_TEST_URL", "redis://127.0.0.1:16379/0")
    redis = Redis.from_url(redis_url, decode_responses=True)
    prefix = f"test:portal:{uuid4().hex}"
    store = RedisAuthTransactionStore(redis, key_prefix=f"{prefix}:tx")
    nce = MockNCEClient()
    boarding = BoardingPassAuthenticationService(
        verifier=MockBoardingPassClient(),
        nce=nce,
        store=store,
        pii_hash_secret="test-pii-secret",
        transaction_ttl_seconds=300,
        guest_valid_minutes=480,
    )
    passport = PassportAuthenticationService(
        ocr=MockPassportOCRClient(),
        nce=nce,
        store=store,
        pii_hash_secret="test-pii-secret",
        transaction_ttl_seconds=300,
        guest_valid_minutes=480,
    )
    wechat = WeChatAuthService(
        store=store,
        pii_hash_secret="test-pii-secret",
        callback_secret="test-wechat-secret",
        transaction_ttl_seconds=300,
    )
    limiter = RedisSlidingWindowRateLimiter(redis, key_prefix=f"{prefix}:rate")
    replay = RedisReplayProtector(redis, key_prefix=f"{prefix}:nonce")
    monkeypatch.setattr(settings, "PII_HASH_SECRET", "test-pii-secret")
    monkeypatch.setattr(settings, "WECHAT_CALLBACK_SECRET", "test-wechat-secret")

    app = FastAPI()
    app.add_exception_handler(RiskControlError, RiskControlHandle)
    app.add_exception_handler(HTTPException, HttpExcHandle)
    app.include_router(portal_router, prefix="/api/v1/portal")
    app.dependency_overrides[get_boarding_pass_service] = lambda: boarding
    app.dependency_overrides[get_passport_service] = lambda: passport
    app.dependency_overrides[get_wechat_service] = lambda: wechat
    app.dependency_overrides[get_rate_limiter] = lambda: limiter
    app.dependency_overrides[get_replay_protector] = lambda: replay

    try:
        async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://test") as client:
            boarding_response = await client.post(
                "/api/v1/portal/boarding-pass/verify",
                json={
                    "flightDate": "2026-09-10",
                    "flightNo": "CA1234",
                    "seatNo": "16A",
                    "documentLast4": "5678",
                    "clientIp": "10.1.2.3",
                    "clientMac": "AA-BB-CC-DD-EE-FF",
                    "ssid": "Airport-Free-WiFi",
                },
            )
            passport_response = await client.post(
                "/api/v1/portal/passport/verify",
                content=b"\xff\xd8\xffmock-passport",
                headers={
                    "Content-Type": "image/jpeg",
                    "X-Client-IP": "10.1.2.4",
                    "X-Client-MAC": "AA-BB-CC-DD-EE-02",
                    "X-SSID": "Airport-Free-WiFi",
                },
            )
            start_response = await client.post(
                "/api/v1/portal/wechat/auth/start",
                json={
                    "clientIp": "10.1.2.5",
                    "clientMac": "AA-BB-CC-DD-EE-03",
                    "ssid": "Airport-Free-WiFi",
                },
            )
            auth_tx_id = start_response.json()["data"]["authTxId"]
            timestamp = str(int(time.time()))
            nonce = "wechat-nonce-001"
            callback_body = json.dumps(
                {"authTxId": auth_tx_id, "result": "SUCCESS", "nceSuccess": True},
                separators=(",", ":"),
            ).encode("utf-8")
            callback_response = await client.post(
                "/api/v1/portal/wechat/auth/callback",
                content=callback_body,
                headers={
                    "Content-Type": "application/json",
                    "X-Wx-Timestamp": timestamp,
                    "X-Wx-Nonce": nonce,
                    "X-Wx-Signature": build_wechat_signature("test-wechat-secret", timestamp, nonce, callback_body),
                },
            )
            status_response = await client.get(
                "/api/v1/portal/wechat/auth/status",
                params={"auth_tx_id": auth_tx_id},
            )

        assert boarding_response.status_code == 200
        assert passport_response.status_code == 200
        assert callback_response.status_code == 200
        assert status_response.json()["data"]["status"] == "SUCCESS"
        all_keys = await redis.keys(f"{prefix}:*")
        dump_parts = []
        for key in all_keys:
            dump_parts.append(repr(await redis.dump(key)))
        dumps = "".join(dump_parts)
        assert "5678" not in dumps
        assert "mock-passport" not in dumps
    finally:
        keys = await redis.keys(f"{prefix}:*")
        if keys:
            await redis.delete(*keys)
        await redis.aclose()
