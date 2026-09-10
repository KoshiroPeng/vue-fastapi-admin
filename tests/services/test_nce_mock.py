from datetime import datetime, timedelta, timezone

import pytest
from pydantic import ValidationError

from app.services.nce.client import (
    NCEGuestCreateRequest,
    NCEHealthStatus,
    NCERadiusLogQuery,
    NCEUserQuery,
)
from app.services.nce.errors import (
    NCEAuthenticationError,
    NCEBusinessError,
    NCETimeoutError,
    NCEUnavailableError,
)
from app.services.nce.mock import MockNCEClient, MockNCEScenario


@pytest.mark.asyncio
async def test_mock_nce_reports_healthy_without_real_nce() -> None:
    client = MockNCEClient()

    health = await client.health()

    assert health.status is NCEHealthStatus.HEALTHY
    assert health.mode == "mock"
    assert health.configured is True
    assert health.message == "NCE Mock 服务可用"


@pytest.mark.asyncio
async def test_mock_nce_creates_deterministic_24_hour_guest() -> None:
    now = datetime(2026, 9, 10, 8, 0, tzinfo=timezone.utc)
    client = MockNCEClient(clock=lambda: now)

    guest = await client.create_guest(
        NCEGuestCreateRequest(
            request_id="request-001",
            username_prefix="kiosk",
            valid_duration_minutes=1440,
            max_devices=1,
            description="Kiosk Self-service",
        )
    )

    assert guest.username == "kiosk_89253c07"
    assert guest.password.get_secret_value() == "Mock-89253c07"
    assert "Mock-89253c07" not in repr(guest)
    assert guest.valid_until == datetime(2026, 9, 11, 8, 0, tzinfo=timezone.utc)
    assert guest.max_devices == 1


@pytest.mark.asyncio
async def test_mock_nce_can_simulate_dependency_outage() -> None:
    client = MockNCEClient(scenario=MockNCEScenario.UNAVAILABLE)

    health = await client.health()

    assert health.status is NCEHealthStatus.DOWN
    assert health.configured is True
    assert health.message == "NCE Mock 模拟不可用"


@pytest.mark.asyncio
async def test_mock_token_is_secret_and_has_expiry() -> None:
    now = datetime(2026, 9, 10, 8, 0, tzinfo=timezone.utc)
    token = await MockNCEClient(clock=lambda: now).get_access_token()

    assert token.value.get_secret_value() == "mock-nce-access-token"
    assert "mock-nce-access-token" not in repr(token)
    assert token.expires_at == now + timedelta(minutes=30)


@pytest.mark.asyncio
async def test_mock_online_users_support_filtering_and_pagination() -> None:
    client = MockNCEClient()

    page = await client.query_users(NCEUserQuery(online_only=True, page=1, page_size=2))

    assert len(page.items) == 2
    assert page.total == 3
    assert all(item.is_online for item in page.items)
    assert all("password" not in item.model_dump() for item in page.items)
    grouped = await client.query_users(NCEUserQuery(user_group_id="mock-guest-group", page_size=10))
    assert grouped.total == 4


@pytest.mark.asyncio
async def test_mock_radius_logs_use_opaque_cursor() -> None:
    start = datetime(2026, 9, 10, 0, 0, tzinfo=timezone.utc)
    client = MockNCEClient()

    first = await client.query_radius_logs(
        NCERadiusLogQuery(
            site_id="mock-site",
            start_time=start,
            end_time=start + timedelta(days=1),
            page_size=2,
        )
    )
    second = await client.query_radius_logs(
        NCERadiusLogQuery(
            site_id="mock-site",
            start_time=start,
            end_time=start + timedelta(days=1),
            page_size=2,
            cursor=first.next_cursor,
        )
    )

    assert len(first.items) == 2
    assert first.next_cursor is not None
    assert len(second.items) == 2
    assert second.next_cursor is None
    assert {item.id for item in first.items}.isdisjoint(item.id for item in second.items)

    filtered = await client.query_radius_logs(
        NCERadiusLogQuery(
            site_id="mock-site",
            start_time=start,
            end_time=start + timedelta(days=1),
            user_name="kiosk_mock",
            terminal_ip="10.85.73.10",
            terminal_mac="AA-BB-CC-DD-EE-03",
        )
    )
    assert [item.id for item in filtered.items] == ["radius-003"]

    with pytest.raises(NCEBusinessError, match="无效的 NCE Mock 游标"):
        await client.query_radius_logs(
            NCERadiusLogQuery(
                site_id="mock-site",
                start_time=start,
                end_time=start + timedelta(days=1),
                cursor="not-valid-base64!",
            )
        )


def test_radius_query_rejects_ranges_longer_than_seven_days() -> None:
    start = datetime(2026, 9, 1, tzinfo=timezone.utc)

    with pytest.raises(ValidationError, match="7 天"):
        NCERadiusLogQuery(
            site_id="mock-site",
            start_time=start,
            end_time=start + timedelta(days=8),
        )


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("scenario", "expected_error"),
    [
        (MockNCEScenario.AUTH_FAILURE, NCEAuthenticationError),
        (MockNCEScenario.BUSINESS_FAILURE, NCEBusinessError),
        (MockNCEScenario.TIMEOUT, NCETimeoutError),
        (MockNCEScenario.UNAVAILABLE, NCEUnavailableError),
    ],
)
async def test_mock_scenarios_raise_typed_errors(scenario: MockNCEScenario, expected_error: type[Exception]) -> None:
    client = MockNCEClient(scenario=scenario)

    with pytest.raises(expected_error):
        await client.create_guest(
            NCEGuestCreateRequest(
                request_id="request-001",
                username_prefix="kiosk",
                valid_duration_minutes=1440,
                max_devices=1,
                description="Kiosk Self-service",
            )
        )
