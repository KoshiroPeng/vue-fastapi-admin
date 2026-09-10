import base64
import binascii
import hashlib
from collections.abc import Callable
from datetime import datetime, timedelta, timezone
from enum import Enum

from app.core.request_context import get_request_id
from app.log import logger

from .client import (
    NCEAccessToken,
    NCEGuest,
    NCEGuestCreateRequest,
    NCEHealth,
    NCEHealthStatus,
    NCERadiusLog,
    NCERadiusLogPage,
    NCERadiusLogQuery,
    NCEUser,
    NCEUserPage,
    NCEUserQuery,
)
from .errors import NCEAuthenticationError, NCEBusinessError, NCETimeoutError, NCEUnavailableError


class MockNCEScenario(str, Enum):
    HEALTHY = "healthy"
    AUTH_FAILURE = "auth_failure"
    BUSINESS_FAILURE = "business_failure"
    TIMEOUT = "timeout"
    UNAVAILABLE = "unavailable"


class MockNCEClient:
    """Deterministic NCE substitute for development and automated tests."""

    def __init__(
        self,
        clock: Callable[[], datetime] | None = None,
        scenario: MockNCEScenario = MockNCEScenario.HEALTHY,
    ) -> None:
        self._clock = clock or (lambda: datetime.now(timezone.utc))
        self._scenario = scenario

    async def health(self) -> NCEHealth:
        status_messages = {
            MockNCEScenario.HEALTHY: (NCEHealthStatus.HEALTHY, "NCE Mock 服务可用"),
            MockNCEScenario.AUTH_FAILURE: (NCEHealthStatus.DEGRADED, "NCE Mock 模拟鉴权失败"),
            MockNCEScenario.BUSINESS_FAILURE: (NCEHealthStatus.DEGRADED, "NCE Mock 模拟业务失败"),
            MockNCEScenario.TIMEOUT: (NCEHealthStatus.DOWN, "NCE Mock 模拟超时"),
            MockNCEScenario.UNAVAILABLE: (NCEHealthStatus.DOWN, "NCE Mock 模拟不可用"),
        }
        status, message = status_messages[self._scenario]
        return NCEHealth(status=status, mode="mock", configured=True, latency_ms=0, message=message)

    async def get_access_token(self) -> NCEAccessToken:
        self._raise_for_scenario("get_access_token")
        return NCEAccessToken(value="mock-nce-access-token", expires_at=self._clock() + timedelta(minutes=30))

    async def create_guest(self, request: NCEGuestCreateRequest) -> NCEGuest:
        self._raise_for_scenario("create_guest")
        request_digest = hashlib.sha256(request.request_id.encode("utf-8")).hexdigest()[:8]
        logger.info(
            "event=nce_mock_guest_created request_id={} operation_id={} valid_minutes={} max_devices={}",
            get_request_id() or "-",
            request.request_id,
            request.valid_duration_minutes,
            request.max_devices,
        )
        return NCEGuest(
            username=f"{request.username_prefix}_{request_digest}",
            password=f"Mock-{request_digest}",
            valid_until=self._clock() + timedelta(minutes=request.valid_duration_minutes),
            max_devices=request.max_devices,
        )

    async def query_users(self, query: NCEUserQuery) -> NCEUserPage:
        self._raise_for_scenario("query_users")
        users = self._users()
        if query.user_name:
            needle = query.user_name.casefold()
            users = [item for item in users if needle in item.user_name.casefold()]
        if query.user_group_id:
            users = [item for item in users if item.user_group_id == query.user_group_id]
        if query.online_only:
            users = [item for item in users if item.is_online]
        start = (query.page - 1) * query.page_size
        end = start + query.page_size
        return NCEUserPage(
            items=users[start:end],
            total=len(users),
            page=query.page,
            page_size=query.page_size,
        )

    async def query_radius_logs(self, query: NCERadiusLogQuery) -> NCERadiusLogPage:
        self._raise_for_scenario("query_radius_logs")
        items = [
            item
            for item in self._radius_logs()
            if query.start_time <= item.authenticated_at <= query.end_time
            and (query.auth_result == "all" or item.auth_result_code == (0 if query.auth_result == "success" else 1))
            and (query.fail_reason_code is None or item.fail_reason_code == query.fail_reason_code)
            and (query.user_type_code is None or item.user_type_code == query.user_type_code)
            and (query.auth_type_code is None or item.auth_type_code == query.auth_type_code)
        ]
        offset = self._decode_cursor(query.cursor)
        page_items = items[offset : offset + query.page_size]
        next_offset = offset + len(page_items)
        next_cursor = self._encode_cursor(next_offset) if next_offset < len(items) else None
        return NCERadiusLogPage(items=page_items, next_cursor=next_cursor, page_size=query.page_size)

    def _raise_for_scenario(self, operation: str) -> None:
        if self._scenario is MockNCEScenario.HEALTHY:
            return
        logger.warning(
            "event=nce_mock_failure request_id={} operation={} scenario={}",
            get_request_id() or "-",
            operation,
            self._scenario.value,
        )
        if self._scenario is MockNCEScenario.AUTH_FAILURE:
            raise NCEAuthenticationError("NCE Mock 模拟鉴权失败")
        if self._scenario is MockNCEScenario.BUSINESS_FAILURE:
            raise NCEBusinessError("MOCK_BUSINESS_ERROR")
        if self._scenario is MockNCEScenario.TIMEOUT:
            raise NCETimeoutError("NCE Mock 模拟请求超时")
        raise NCEUnavailableError("NCE Mock 模拟服务不可用")

    @staticmethod
    def _encode_cursor(offset: int) -> str:
        return base64.urlsafe_b64encode(f"mock:{offset}".encode("ascii")).decode("ascii")

    @staticmethod
    def _decode_cursor(cursor: str | None) -> int:
        if cursor is None:
            return 0
        try:
            decoded = base64.urlsafe_b64decode(cursor.encode("ascii")).decode("ascii")
            prefix, offset = decoded.split(":", maxsplit=1)
            if prefix != "mock" or int(offset) < 0:
                raise ValueError
            return int(offset)
        except (binascii.Error, ValueError, UnicodeError) as exc:
            raise NCEBusinessError("MOCK_CURSOR_INVALID", "无效的 NCE Mock 游标") from exc

    @staticmethod
    def _users() -> list[NCEUser]:
        base_time = datetime(2026, 9, 10, 7, 30, tzinfo=timezone.utc)
        return [
            NCEUser(
                id="user-001",
                user_name="sms_13800000001",
                user_group_id="mock-guest-group",
                user_group_name="Guest",
                user_type_code=1,
                is_online=True,
                terminal_ip="10.85.73.8",
                terminal_mac="AA-BB-CC-DD-EE-01",
                access_ssid="Airport-Free-WiFi",
                connected_at=base_time,
            ),
            NCEUser(
                id="user-002",
                user_name="wx_mock_002",
                user_group_id="mock-guest-group",
                user_group_name="Guest",
                user_type_code=5,
                is_online=True,
                terminal_ip="10.85.73.9",
                terminal_mac="AA-BB-CC-DD-EE-02",
                access_ssid="Airport-Free-WiFi",
                connected_at=base_time + timedelta(minutes=5),
            ),
            NCEUser(
                id="user-003",
                user_name="kiosk_mock_003",
                user_group_id="mock-guest-group",
                user_group_name="Guest",
                user_type_code=20,
                is_online=True,
                terminal_ip="10.85.73.10",
                terminal_mac="AA-BB-CC-DD-EE-03",
                access_ssid="Airport-Free-WiFi",
                connected_at=base_time + timedelta(minutes=10),
            ),
            NCEUser(
                id="user-004",
                user_name="bp_mock_004",
                user_group_id="mock-guest-group",
                user_group_name="Guest",
                user_type_code=20,
                is_online=False,
            ),
        ]

    @staticmethod
    def _radius_logs() -> list[NCERadiusLog]:
        base_time = datetime(2026, 9, 10, 1, 0, tzinfo=timezone.utc)
        return [
            NCERadiusLog(
                id="radius-001",
                user_name="sms_13800000001",
                user_group_name="Guest",
                user_type_code=1,
                terminal_ip="10.85.73.8",
                terminal_mac="AA-BB-CC-DD-EE-01",
                auth_type_code=11,
                access_ssid="Airport-Free-WiFi",
                authenticated_at=base_time,
                auth_result_code=0,
                fail_reason_code=0,
            ),
            NCERadiusLog(
                id="radius-002",
                user_name="wx_mock_002",
                user_group_name="Guest",
                user_type_code=5,
                terminal_ip="10.85.73.9",
                terminal_mac="AA-BB-CC-DD-EE-02",
                auth_type_code=11,
                access_ssid="Airport-Free-WiFi",
                authenticated_at=base_time + timedelta(hours=1),
                auth_result_code=1,
                fail_reason_code=642,
            ),
            NCERadiusLog(
                id="radius-003",
                user_name="kiosk_mock_003",
                user_group_name="Guest",
                user_type_code=20,
                terminal_ip="10.85.73.10",
                terminal_mac="AA-BB-CC-DD-EE-03",
                auth_type_code=11,
                access_ssid="Airport-Free-WiFi",
                authenticated_at=base_time + timedelta(hours=2),
                auth_result_code=0,
                fail_reason_code=0,
            ),
            NCERadiusLog(
                id="radius-004",
                user_name="bp_mock_004",
                user_group_name="Guest",
                user_type_code=20,
                terminal_ip="10.85.73.11",
                terminal_mac="AA-BB-CC-DD-EE-04",
                auth_type_code=11,
                access_ssid="Airport-Free-WiFi",
                authenticated_at=base_time + timedelta(hours=3),
                auth_result_code=1,
                fail_reason_code=116,
            ),
        ]
