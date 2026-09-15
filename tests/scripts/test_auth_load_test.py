import asyncio
from argparse import Namespace

import httpx
import pytest
from fastapi import FastAPI

from scripts.auth_load_test import (
    RequestResult,
    Thresholds,
    build_request,
    percentile,
    send_request,
    summarize,
    synthetic_client,
)


def make_args(scenario: str) -> Namespace:
    return Namespace(
        scenario=scenario,
        flight_date="2026-09-10",
        flight_no="CA1234",
        seat_no="16A",
        document_last4="5678",
        ssid="Airport-Free-WiFi",
        passport_content_type="image/jpeg",
    )


def test_percentile_uses_nearest_rank() -> None:
    values = [float(value) for value in range(1, 101)]

    assert percentile(values, 50) == 50
    assert percentile(values, 95) == 95
    assert percentile(values, 99) == 99
    assert percentile([], 95) == 0


def test_synthetic_clients_are_unique_and_use_private_addresses() -> None:
    first = synthetic_client(0)
    second = synthetic_client(1)

    assert first != second
    assert first[0].startswith("10.")
    assert first[1].startswith("02:")
    assert first[2].startswith("06:")


def test_mixed_scenario_alternates_complete_authentication_requests() -> None:
    args = make_args("mixed")

    boarding_path, boarding = build_request(0, args, b"image")
    passport_path, passport = build_request(1, args, b"image")

    assert boarding_path.endswith("/boarding-pass/verify")
    assert boarding["json"]["deviceMac"]
    assert passport_path.endswith("/passport/verify")
    assert passport["content"] == b"image"
    assert passport["headers"]["X-Device-MAC"]


def test_summary_passes_when_business_and_latency_thresholds_are_met() -> None:
    results = [RequestResult(float(value), True, 200) for value in range(1, 101)]

    report, violations = summarize(
        results,
        target_rps=50,
        configured_duration_seconds=2,
        actual_elapsed_seconds=2.1,
        scenario="mixed",
        concurrency=50,
        thresholds=Thresholds(max_error_rate=0.01, max_p95_ms=1000, max_p99_ms=2000),
    )

    assert violations == []
    assert report["passed"] is True
    assert report["latencyMs"]["p95"] == 95
    assert report["successful"] == 100
    assert report["statusCounts"] == {"200": 100}


def test_summary_fails_on_business_errors_or_latency() -> None:
    results = [RequestResult(2500, False, 502, "HTTP 502"), RequestResult(2100, True, 200)]

    report, violations = summarize(
        results,
        target_rps=50,
        configured_duration_seconds=1,
        actual_elapsed_seconds=2.5,
        scenario="boarding-pass",
        concurrency=50,
        thresholds=Thresholds(max_error_rate=0.01, max_p95_ms=1000, max_p99_ms=2000),
    )

    assert report["passed"] is False
    assert report["errorExamples"] == ["HTTP 502"]
    assert report["statusCounts"] == {"502": 1, "200": 1}
    assert len(violations) == 3


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("response_body", "expected_success", "expected_error"),
    [
        ({"data": {"networkAuthorized": True}}, True, None),
        ({"data": {"networkAuthorized": False}}, False, "networkAuthorized 不为 true"),
    ],
)
async def test_send_request_checks_business_authorization_result(
    response_body: dict,
    expected_success: bool,
    expected_error: str | None,
) -> None:
    app = FastAPI()

    @app.post("/api/v1/portal/boarding-pass/verify")
    async def verify() -> dict:
        return response_body

    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
        result = await send_request(client, asyncio.Semaphore(1), 0, make_args("boarding-pass"), b"")

    assert result.successful is expected_success
    assert result.error == expected_error
