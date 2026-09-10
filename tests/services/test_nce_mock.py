from datetime import datetime, timezone

import pytest

from app.services.nce.client import NCEGuestCreateRequest, NCEHealthStatus
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
    assert guest.password == "Mock-89253c07"
    assert guest.valid_until == datetime(2026, 9, 11, 8, 0, tzinfo=timezone.utc)
    assert guest.max_devices == 1


@pytest.mark.asyncio
async def test_mock_nce_can_simulate_dependency_outage() -> None:
    client = MockNCEClient(scenario=MockNCEScenario.UNAVAILABLE)

    health = await client.health()

    assert health.status is NCEHealthStatus.DOWN
    assert health.configured is True
    assert health.message == "NCE Mock 模拟不可用"
