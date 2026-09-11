import json
from unittest.mock import AsyncMock

import pytest

from app.api import health


@pytest.mark.asyncio
async def test_readiness_reports_ready_when_dependencies_are_available(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(health, "check_mysql", AsyncMock())
    monkeypatch.setattr(health, "check_redis", AsyncMock())

    response = await health.readiness()

    assert response.status_code == 200
    assert json.loads(response.body) == {"status": "ready"}


@pytest.mark.asyncio
async def test_readiness_identifies_failed_dependency(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(health, "check_mysql", AsyncMock(side_effect=ConnectionError("database unavailable")))
    monkeypatch.setattr(health, "check_redis", AsyncMock())

    response = await health.readiness()

    assert response.status_code == 503
    assert json.loads(response.body) == {"status": "not_ready", "failed_dependencies": ["mysql"]}
