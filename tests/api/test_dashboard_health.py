import httpx
import pytest
from fastapi import FastAPI

from app.api.v1.dashboard import dashboard_router
from app.api.v1.runtime_config import runtime_config_router
from app.services.health import DependencyHealth, DependencyHealthStatus, get_redis_health


@pytest.mark.asyncio
async def test_dashboard_health_uses_nce_mock() -> None:
    app = FastAPI()
    app.include_router(dashboard_router, prefix="/api/v1/dashboard")
    app.dependency_overrides[get_redis_health] = lambda: DependencyHealth(
        status=DependencyHealthStatus.HEALTHY,
        configured=True,
        latency_ms=1,
        message="Redis 服务可用",
    )

    async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://test") as client:
        response = await client.get("/api/v1/dashboard/health")

    assert response.status_code == 200
    assert response.json() == {
        "code": 200,
        "msg": "OK",
        "data": {
            "nce": {
                "status": "healthy",
                "mode": "mock",
                "configured": True,
                "latency_ms": 0,
                "message": "NCE Mock 服务可用",
            },
            "redis": {
                "status": "healthy",
                "configured": True,
                "latency_ms": 1,
                "message": "Redis 服务可用",
            },
        },
    }


@pytest.mark.asyncio
async def test_runtime_config_api_returns_only_safe_summary() -> None:
    app = FastAPI()
    app.include_router(runtime_config_router, prefix="/api/v1/runtime-config")

    async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://test") as client:
        response = await client.get("/api/v1/runtime-config/summary")

    assert response.status_code == 200
    data = response.json()["data"]
    assert data["nce_mode"] == "mock"
    assert "NCE_PASSWORD" not in response.text
    assert "KIOSK_HMAC_SECRET" not in response.text
