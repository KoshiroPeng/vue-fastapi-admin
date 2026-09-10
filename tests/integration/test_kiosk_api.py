import json
import os
import time
from datetime import datetime, timezone
from uuid import uuid4

import httpx
import pytest
from fastapi import FastAPI, HTTPException
from redis.asyncio import Redis

from app.api.v1.kiosk import kiosk_router
from app.core.exceptions import HttpExcHandle, RiskControlHandle
from app.services.kiosk.signing import build_kiosk_signature
from app.services.nce import get_nce_client
from app.services.nce.mock import MockNCEClient
from app.services.risk_control import (
    RedisIdempotencyGuard,
    RedisReplayProtector,
    RedisSlidingWindowRateLimiter,
    RiskControlError,
    get_idempotency_guard,
    get_rate_limiter,
    get_replay_protector,
)
from app.settings import settings

pytestmark = pytest.mark.skipif(
    os.getenv("RUN_REDIS_INTEGRATION") != "1",
    reason="set RUN_REDIS_INTEGRATION=1 to test against an available Redis",
)


@pytest.mark.asyncio
async def test_signed_kiosk_request_creates_mock_nce_guest(monkeypatch: pytest.MonkeyPatch) -> None:
    redis_url = os.getenv("REDIS_TEST_URL", "redis://127.0.0.1:16379/0")
    redis = Redis.from_url(redis_url, decode_responses=True)
    test_prefix = f"test:kiosk:{uuid4().hex}"
    timestamp = str(int(time.time()))
    nonce = "nonce-001"
    idempotency_key = "request-001"
    body = json.dumps(
        {"idType": "ID_CARD", "idDigest": "a" * 64},
        separators=(",", ":"),
    ).encode("utf-8")
    signature = build_kiosk_signature(
        secret="test-kiosk-secret",
        method="POST",
        path="/api/v1/kiosk/create-guest",
        kiosk_id="KIOSK-T3-001",
        timestamp=timestamp,
        nonce=nonce,
        idempotency_key=idempotency_key,
        body=body,
    )

    monkeypatch.setattr(settings, "KIOSK_HMAC_SECRET", "test-kiosk-secret")
    monkeypatch.setattr(settings, "PII_HASH_SECRET", "test-pii-secret")
    monkeypatch.setattr(settings, "KIOSK_ALLOWED_IPS", ["127.0.0.1"])
    app = FastAPI()
    app.add_exception_handler(RiskControlError, RiskControlHandle)
    app.add_exception_handler(HTTPException, HttpExcHandle)
    app.include_router(kiosk_router, prefix="/api/v1/kiosk")
    app.dependency_overrides[get_nce_client] = lambda: MockNCEClient(
        clock=lambda: datetime(2026, 9, 10, 8, 0, tzinfo=timezone.utc)
    )
    app.dependency_overrides[get_replay_protector] = lambda: RedisReplayProtector(
        redis, key_prefix=f"{test_prefix}:nonce"
    )
    app.dependency_overrides[get_rate_limiter] = lambda: RedisSlidingWindowRateLimiter(
        redis, key_prefix=f"{test_prefix}:rate"
    )
    app.dependency_overrides[get_idempotency_guard] = lambda: RedisIdempotencyGuard(
        redis, key_prefix=f"{test_prefix}:idempotency"
    )

    try:
        async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://test") as client:
            response = await client.post(
                "/api/v1/kiosk/create-guest",
                content=body,
                headers={
                    "Content-Type": "application/json",
                    "X-Kiosk-Id": "KIOSK-T3-001",
                    "X-Timestamp": timestamp,
                    "X-Nonce": nonce,
                    "X-Signature": signature,
                    "Idempotency-Key": idempotency_key,
                },
            )

        assert response.status_code == 200
        data = response.json()["data"]
        assert data["username"].startswith("kiosk_")
        assert data["password"].startswith("Mock-")
        assert data["validDurationMinutes"] == 1440
        assert data["maxDevices"] == 1

        async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://test") as client:
            replay_response = await client.post(
                "/api/v1/kiosk/create-guest",
                content=body,
                headers={
                    "Content-Type": "application/json",
                    "X-Kiosk-Id": "KIOSK-T3-001",
                    "X-Timestamp": timestamp,
                    "X-Nonce": nonce,
                    "X-Signature": signature,
                    "Idempotency-Key": idempotency_key,
                },
            )
        assert replay_response.status_code == 409
        assert replay_response.json()["error_code"] == "REPLAY_DETECTED"

        second_nonce = "nonce-002"
        second_signature = build_kiosk_signature(
            secret="test-kiosk-secret",
            method="POST",
            path="/api/v1/kiosk/create-guest",
            kiosk_id="KIOSK-T3-001",
            timestamp=timestamp,
            nonce=second_nonce,
            idempotency_key=idempotency_key,
            body=body,
        )
        async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://test") as client:
            duplicate_response = await client.post(
                "/api/v1/kiosk/create-guest",
                content=body,
                headers={
                    "Content-Type": "application/json",
                    "X-Kiosk-Id": "KIOSK-T3-001",
                    "X-Timestamp": timestamp,
                    "X-Nonce": second_nonce,
                    "X-Signature": second_signature,
                    "Idempotency-Key": idempotency_key,
                },
            )
        assert duplicate_response.status_code == 409
        assert duplicate_response.json()["error_code"] == "IDEMPOTENCY_CONFLICT"

        async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://test") as client:
            tampered_response = await client.post(
                "/api/v1/kiosk/create-guest",
                content=body + b" ",
                headers={
                    "Content-Type": "application/json",
                    "X-Kiosk-Id": "KIOSK-T3-001",
                    "X-Timestamp": timestamp,
                    "X-Nonce": "nonce-003",
                    "X-Signature": signature,
                    "Idempotency-Key": "request-003",
                },
            )
        assert tampered_response.status_code == 401

        blocked_nonce = "nonce-004"
        blocked_key = "request-004"
        blocked_signature = build_kiosk_signature(
            secret="test-kiosk-secret",
            method="POST",
            path="/api/v1/kiosk/create-guest",
            kiosk_id="KIOSK-T3-001",
            timestamp=timestamp,
            nonce=blocked_nonce,
            idempotency_key=blocked_key,
            body=body,
        )
        blocked_transport = httpx.ASGITransport(app=app, client=("10.0.0.9", 12345))
        async with httpx.AsyncClient(transport=blocked_transport, base_url="http://test") as client:
            blocked_response = await client.post(
                "/api/v1/kiosk/create-guest",
                content=body,
                headers={
                    "Content-Type": "application/json",
                    "X-Kiosk-Id": "KIOSK-T3-001",
                    "X-Timestamp": timestamp,
                    "X-Nonce": blocked_nonce,
                    "X-Signature": blocked_signature,
                    "Idempotency-Key": blocked_key,
                },
            )
        assert blocked_response.status_code == 403

        proxy_transport = httpx.ASGITransport(app=app, client=("127.0.0.1", 12345))
        async with httpx.AsyncClient(transport=proxy_transport, base_url="http://test") as client:
            forwarded_response = await client.post(
                "/api/v1/kiosk/create-guest",
                content=body,
                headers={
                    "Content-Type": "application/json",
                    "X-Forwarded-For": "10.0.0.9",
                    "X-Kiosk-Id": "KIOSK-T3-001",
                    "X-Timestamp": timestamp,
                    "X-Nonce": blocked_nonce,
                    "X-Signature": blocked_signature,
                    "Idempotency-Key": blocked_key,
                },
            )
        assert forwarded_response.status_code == 403

        oversized_body = json.dumps(
            {"idType": "ID_CARD", "idDigest": "b" * 64, "padding": "x" * 9000},
            separators=(",", ":"),
        ).encode("utf-8")
        oversized_signature = build_kiosk_signature(
            secret="test-kiosk-secret",
            method="POST",
            path="/api/v1/kiosk/create-guest",
            kiosk_id="KIOSK-T3-001",
            timestamp=timestamp,
            nonce="nonce-005",
            idempotency_key="request-005",
            body=oversized_body,
        )
        async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://test") as client:
            oversized_response = await client.post(
                "/api/v1/kiosk/create-guest",
                content=oversized_body,
                headers={
                    "Content-Type": "application/json",
                    "X-Kiosk-Id": "KIOSK-T3-001",
                    "X-Timestamp": timestamp,
                    "X-Nonce": "nonce-005",
                    "X-Signature": oversized_signature,
                    "Idempotency-Key": "request-005",
                },
            )
        assert oversized_response.status_code == 413

        keys = await redis.keys(f"{test_prefix}:*")
        dumps = []
        for key in keys:
            dumps.append(repr(await redis.dump(key)))
        stored = "".join(keys) + "".join(dumps)
        assert "a" * 64 not in stored
    finally:
        keys = await redis.keys(f"{test_prefix}:*")
        if keys:
            await redis.delete(*keys)
        await redis.aclose()
