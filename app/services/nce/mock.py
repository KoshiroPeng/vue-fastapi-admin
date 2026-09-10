import hashlib
from collections.abc import Callable
from datetime import datetime, timedelta, timezone
from enum import Enum

from app.log import logger

from .client import NCEGuest, NCEGuestCreateRequest, NCEHealth, NCEHealthStatus


class MockNCEScenario(str, Enum):
    HEALTHY = "healthy"
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
        if self._scenario is MockNCEScenario.UNAVAILABLE:
            return NCEHealth(
                status=NCEHealthStatus.DOWN,
                mode="mock",
                configured=True,
                latency_ms=0,
                message="NCE Mock 模拟不可用",
            )

        return NCEHealth(
            status=NCEHealthStatus.HEALTHY,
            mode="mock",
            configured=True,
            latency_ms=0,
            message="NCE Mock 服务可用",
        )

    async def create_guest(self, request: NCEGuestCreateRequest) -> NCEGuest:
        request_digest = hashlib.sha256(request.request_id.encode("utf-8")).hexdigest()[:8]
        logger.info(
            "event=nce_mock_guest_created request_id={} valid_minutes={} max_devices={}",
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
