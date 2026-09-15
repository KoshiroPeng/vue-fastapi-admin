import asyncio
import base64
import json
from datetime import datetime, timedelta, timezone

import httpx
import pytest
from pydantic import SecretStr

from app.services.nce import (
    NCEAuthenticationError,
    NCEAuthorizationStatus,
    NCEBusinessError,
    NCEGuestCreateRequest,
    NCEProtocolError,
    NCERadiusLogQuery,
    NCETerminalAuthorizationRequest,
    NCETimeoutError,
    NCEUnavailableError,
    NCEUserQuery,
)
from app.services.nce.authorization import authorize_terminal_and_wait
from app.services.nce.http_client import HuaweiNCEHttpClient


NOW = datetime(2026, 9, 15, 1, 0, tzinfo=timezone.utc)


def _token_response(token: str = "token-1", expires_at: datetime | None = None) -> httpx.Response:
    expiry = expires_at or NOW + timedelta(hours=1)
    return httpx.Response(
        200,
        json={"errcode": "0", "data": {"token_id": token, "expiredDate": int(expiry.timestamp() * 1000)}},
    )


def _client(handler, *, clock=lambda: NOW) -> HuaweiNCEHttpClient:
    return HuaweiNCEHttpClient(
        base_url="https://nce.example",
        username="operator",
        password=SecretStr("nce-password"),
        guest_user_group_id="guest-group",
        credential_secret=SecretStr("credential-secret"),
        timeout=httpx.Timeout(1),
        limits=httpx.Limits(max_connections=20, max_keepalive_connections=10),
        transport=httpx.MockTransport(handler),
        clock=clock,
    )


def _authorization_request(**overrides) -> NCETerminalAuthorizationRequest:
    values = {
        "request_id": "tx-001",
        "username": "bp_user",
        "client_ip": "10.1.2.3",
        "client_mac": "AA-BB-CC-DD-EE-FF",
        "ssid": "机场免费WiFi",
        "device_mac": "11-22-33-44-55-66",
        "ap_mac": "22-33-44-55-66-77",
        "node_ip": "172.16.4.107",
        "policy_name": "guest-policy",
        "permit_seconds": 3600,
    }
    values.update(overrides)
    return NCETerminalAuthorizationRequest(**values)


@pytest.mark.asyncio
async def test_concurrent_token_requests_share_one_refresh() -> None:
    token_calls = 0

    async def handler(request: httpx.Request) -> httpx.Response:
        nonlocal token_calls
        assert request.url.path == HuaweiNCEHttpClient.TOKEN_PATH
        token_calls += 1
        await asyncio.sleep(0)
        return _token_response()

    client = _client(handler)
    try:
        tokens = await asyncio.gather(*(client.get_access_token() for _ in range(20)))
        assert token_calls == 1
        assert {item.value.get_secret_value() for item in tokens} == {"token-1"}
    finally:
        await client.aclose()


@pytest.mark.asyncio
async def test_expiring_token_is_refreshed() -> None:
    current = [NOW]
    token_calls = 0

    def handler(request: httpx.Request) -> httpx.Response:
        nonlocal token_calls
        token_calls += 1
        return _token_response(f"token-{token_calls}", current[0] + timedelta(minutes=2))

    client = _client(handler, clock=lambda: current[0])
    try:
        first = await client.get_access_token()
        current[0] += timedelta(seconds=70)
        second = await client.get_access_token()
        assert first.value.get_secret_value() == "token-1"
        assert second.value.get_secret_value() == "token-2"
        assert token_calls == 2
    finally:
        await client.aclose()


@pytest.mark.asyncio
async def test_concurrent_401_responses_trigger_one_token_refresh() -> None:
    token_calls = 0
    old_token_requests = 0
    both_old_requests = asyncio.Event()

    async def handler(request: httpx.Request) -> httpx.Response:
        nonlocal token_calls, old_token_requests
        if request.url.path == HuaweiNCEHttpClient.TOKEN_PATH:
            token_calls += 1
            return _token_response(f"token-{token_calls}")
        body = json.loads(request.content)
        if request.headers["X-ACCESS-TOKEN"] == "token-1":
            old_token_requests += 1
            if old_token_requests == 2:
                both_old_requests.set()
            await both_old_requests.wait()
            return httpx.Response(401, json={"errcode": "401"})
        return httpx.Response(201, json={"errcode": "0", "data": {"userName": body["userName"]}})

    client = _client(handler)
    requests = [
        NCEGuestCreateRequest(
            request_id=f"tx-{index}",
            username_prefix="bp",
            valid_duration_minutes=60,
            max_devices=1,
            description="test",
        )
        for index in range(2)
    ]
    try:
        guests = await asyncio.gather(*(client.create_guest(request) for request in requests))
        assert len(guests) == 2
        assert token_calls == 2
    finally:
        await client.aclose()


@pytest.mark.asyncio
async def test_create_guest_sends_expected_fields_and_hides_password() -> None:
    captured: dict = {}

    def handler(request: httpx.Request) -> httpx.Response:
        if request.url.path == HuaweiNCEHttpClient.TOKEN_PATH:
            return _token_response()
        captured.update(json.loads(request.content))
        return httpx.Response(201, json={"errcode": "0", "data": {"userName": captured["userName"]}})

    client = _client(handler)
    try:
        guest = await client.create_guest(
            NCEGuestCreateRequest(
                request_id="stable-request-id",
                username_prefix="pass",
                valid_duration_minutes=480,
                max_devices=1,
                description="Passport OCR Verified",
                terminal_mac="AA-BB-CC-DD-EE-FF",
            )
        )
        assert captured["userGroupId"] == "guest-group"
        assert captured["bindInfo"] == {"bindMac": "AABBCCDDEEFF"}
        assert captured["accessType"] == "deny"
        assert captured["password"] not in repr(guest)
        assert "credential-secret" not in repr(client)
        assert guest.password.get_secret_value() == captured["password"]
    finally:
        await client.aclose()


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("client_ip", "ip_field"),
    [("10.1.2.3", "terminalIpV4"), ("2001:db8::10", "terminalIpV6")],
)
async def test_haca_authorization_encodes_ssid_and_selects_ip_family(client_ip: str, ip_field: str) -> None:
    captured: dict = {}

    def handler(request: httpx.Request) -> httpx.Response:
        if request.url.path == HuaweiNCEHttpClient.TOKEN_PATH:
            return _token_response()
        captured.update(json.loads(request.content))
        return httpx.Response(200, json={"errcode": "0", "psessionid": "session-001"})

    client = _client(handler)
    try:
        result = await client.authorize_terminal(_authorization_request(client_ip=client_ip))
        assert result.status is NCEAuthorizationStatus.PENDING
        assert captured[ip_field] == client_ip
        assert captured["ssid"] == base64.b64encode("机场免费WiFi".encode()).decode()
        assert captured["deviceMac"] == "112233445566"
        assert captured["apMac"] == "223344556677"
        assert captured["temPermitTime"] == 3600
    finally:
        await client.aclose()


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("raw_status", "expected_status"),
    [
        ("success", NCEAuthorizationStatus.SUCCESS),
        ("failed", NCEAuthorizationStatus.FAILED),
        ("vendor-new-state", NCEAuthorizationStatus.PENDING),
        (None, NCEAuthorizationStatus.PENDING),
    ],
)
async def test_haca_result_parser_is_conservative(raw_status, expected_status) -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        if request.url.path == HuaweiNCEHttpClient.TOKEN_PATH:
            return _token_response()
        data = {"psessionid": "session-001"}
        if raw_status is not None:
            data["status"] = raw_status
        return httpx.Response(200, json={"errcode": "0", "data": data})

    client = _client(handler)
    try:
        result = await client.query_authorization_result("session-001")
        assert result.status is expected_status
    finally:
        await client.aclose()


@pytest.mark.asyncio
async def test_authorization_polling_times_out_while_status_remains_unknown() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        if request.url.path == HuaweiNCEHttpClient.TOKEN_PATH:
            return _token_response()
        if request.url.path == HuaweiNCEHttpClient.HACA_AUTHORIZATION_PATH:
            return httpx.Response(200, json={"errcode": "0", "psessionid": "session-001"})
        return httpx.Response(
            200,
            json={"errcode": "0", "data": {"psessionid": "session-001", "status": "unknown"}},
        )

    client = _client(handler)
    try:
        with pytest.raises(NCETimeoutError):
            await authorize_terminal_and_wait(
                client,
                _authorization_request(),
                poll_attempts=2,
                poll_interval_ms=0,
            )
    finally:
        await client.aclose()


@pytest.mark.asyncio
async def test_authorization_polling_raises_business_error_on_explicit_failure() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        if request.url.path == HuaweiNCEHttpClient.TOKEN_PATH:
            return _token_response()
        if request.url.path == HuaweiNCEHttpClient.HACA_AUTHORIZATION_PATH:
            return httpx.Response(200, json={"errcode": "0", "psessionid": "session-001"})
        return httpx.Response(
            200,
            json={
                "errcode": "0",
                "data": {"psessionid": "session-001", "status": "failed", "resultCode": "HACA_DENIED"},
            },
        )

    client = _client(handler)
    try:
        with pytest.raises(NCEBusinessError) as error:
            await authorize_terminal_and_wait(
                client,
                _authorization_request(),
                poll_attempts=2,
                poll_interval_ms=0,
            )
        assert error.value.result_code == "HACA_DENIED"
    finally:
        await client.aclose()


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("response", "expected_error"),
    [
        (httpx.Response(400, json={"errcode": "INVALID"}), NCEBusinessError),
        (httpx.Response(401, json={"errcode": "401"}), NCEAuthenticationError),
        (httpx.Response(500, json={"errcode": "500"}), NCEUnavailableError),
        (httpx.Response(200, text="not-json"), NCEProtocolError),
    ],
)
async def test_http_errors_are_classified(response: httpx.Response, expected_error: type[Exception]) -> None:
    token_calls = 0

    def handler(request: httpx.Request) -> httpx.Response:
        nonlocal token_calls
        if request.url.path == HuaweiNCEHttpClient.TOKEN_PATH:
            token_calls += 1
            return _token_response(f"token-{token_calls}")
        return response

    client = _client(handler)
    try:
        with pytest.raises(expected_error):
            await client.create_guest(
                NCEGuestCreateRequest(
                    request_id="tx-error",
                    username_prefix="bp",
                    valid_duration_minutes=60,
                    max_devices=1,
                    description="test",
                )
            )
    finally:
        await client.aclose()


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("transport_error", "expected_error"),
    [
        (httpx.ReadTimeout("timeout"), NCETimeoutError),
        (httpx.ConnectError("connect"), NCEUnavailableError),
    ],
)
async def test_transport_errors_are_classified(transport_error: Exception, expected_error: type[Exception]) -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        if request.url.path == HuaweiNCEHttpClient.TOKEN_PATH:
            return _token_response()
        transport_error.request = request
        raise transport_error

    client = _client(handler)
    try:
        with pytest.raises(expected_error):
            await client.create_guest(
                NCEGuestCreateRequest(
                    request_id="tx-error",
                    username_prefix="bp",
                    valid_duration_minutes=60,
                    max_devices=1,
                    description="test",
                )
            )
    finally:
        await client.aclose()


@pytest.mark.asyncio
async def test_user_and_radius_responses_are_mapped() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        if request.url.path == HuaweiNCEHttpClient.TOKEN_PATH:
            return _token_response()
        if request.url.path == HuaweiNCEHttpClient.USERS_PATH:
            return httpx.Response(
                200,
                json={
                    "errcode": "0",
                    "data": {
                        "total": 1,
                        "items": [
                            {
                                "id": "user-1",
                                "userName": "bp_user",
                                "userGroupId": "group-1",
                                "userGroupName": "Guest",
                                "userTypeCode": 20,
                                "isOnline": True,
                                "terminalIpV4": "10.1.2.3",
                            }
                        ],
                    },
                },
            )
        return httpx.Response(
            200,
            json={
                "errcode": "0",
                "data": [
                    {
                        "id": "log-1",
                        "userName": "bp_user",
                        "userGroupName": "Guest",
                        "userTypeCode": 20,
                        "terminalIpV4": "10.1.2.3",
                        "terminalMac": "AABBCCDDEEFF",
                        "authenTypeCode": 11,
                        "ssid": "Airport-Free-WiFi",
                        "authenTime": int(NOW.timestamp() * 1000),
                        "authenResultCode": 0,
                        "failReasonCode": 0,
                    }
                ],
            },
        )

    client = _client(handler)
    try:
        users = await client.query_users(NCEUserQuery(page=1, page_size=20))
        logs = await client.query_radius_logs(
            NCERadiusLogQuery(
                site_id="site-1",
                start_time=NOW - timedelta(hours=1),
                end_time=NOW + timedelta(hours=1),
            )
        )
        assert users.total == 1
        assert users.items[0].terminal_ip == "10.1.2.3"
        assert logs.items[0].authenticated_at == NOW
    finally:
        await client.aclose()


@pytest.mark.asyncio
async def test_client_close_closes_underlying_pool() -> None:
    client = _client(lambda request: _token_response())
    await client.aclose()
    assert client._client.is_closed is True
