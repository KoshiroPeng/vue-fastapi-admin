from datetime import datetime, timedelta, timezone

import httpx
import pytest
from fastapi import FastAPI

from app.api.v1.dashboard import dashboard_router
from app.core.dependency import DependPermission
from app.services.dashboard import DashboardProxy, get_dashboard_proxy
from app.services.nce.mock import MockNCEClient


@pytest.fixture
def app() -> FastAPI:
    application = FastAPI()
    application.include_router(dashboard_router, prefix="/api/v1/dashboard")
    application.dependency_overrides[get_dashboard_proxy] = lambda: DashboardProxy(MockNCEClient())
    return application


@pytest.mark.asyncio
async def test_online_users_api_returns_masked_page(app: FastAPI) -> None:
    async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://test") as client:
        response = await client.get("/api/v1/dashboard/online-users", params={"page": 1, "page_size": 2})

    assert response.status_code == 200
    data = response.json()["data"]
    assert data["total"] == 3
    assert len(data["items"]) == 2
    assert data["items"][0]["user_name"] == "sms_138****0001"
    assert "13800000001" not in response.text


@pytest.mark.asyncio
async def test_radius_logs_api_returns_masked_cursor_page(app: FastAPI) -> None:
    start = datetime(2026, 9, 10, 0, 0, tzinfo=timezone.utc)
    async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://test") as client:
        response = await client.post(
            "/api/v1/dashboard/radius-logs",
            json={
                "start_time": start.isoformat(),
                "end_time": (start + timedelta(days=1)).isoformat(),
                "page_size": 2,
            },
        )

    assert response.status_code == 200
    data = response.json()["data"]
    assert len(data["items"]) == 2
    assert data["next_cursor"] is not None
    assert data["items"][0]["terminal_mac"] == "AA:**:**:**:**:01"
    assert "AA-BB-CC-DD-EE-01" not in response.text


@pytest.mark.asyncio
async def test_radius_logs_api_applies_sensitive_filters(app: FastAPI) -> None:
    start = datetime(2026, 9, 10, 0, 0, tzinfo=timezone.utc)
    async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://test") as client:
        response = await client.post(
            "/api/v1/dashboard/radius-logs",
            json={
                "start_time": start.isoformat(),
                "end_time": (start + timedelta(days=1)).isoformat(),
                "user_name": "kiosk_mock",
                "terminal_ip": "10.85.73.10",
                "terminal_mac": "AA-BB-CC-DD-EE-03",
            },
        )

    assert response.status_code == 200
    items = response.json()["data"]["items"]
    assert [item["id"] for item in items] == ["radius-003"]
    assert "10.85.73.10" not in response.text
    assert "AA-BB-CC-DD-EE-03" not in response.text


@pytest.mark.asyncio
async def test_dashboard_router_reuses_existing_permission_dependency() -> None:
    protected_app = FastAPI()
    protected_app.include_router(
        dashboard_router,
        prefix="/api/v1/dashboard",
        dependencies=[DependPermission],
    )
    protected_app.dependency_overrides[get_dashboard_proxy] = lambda: DashboardProxy(MockNCEClient())

    async with httpx.AsyncClient(
        transport=httpx.ASGITransport(app=protected_app),
        base_url="http://test",
    ) as client:
        response = await client.get("/api/v1/dashboard/online-users")

    assert response.status_code == 422
    assert "token" in response.text
