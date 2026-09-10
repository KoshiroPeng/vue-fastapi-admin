from datetime import date, datetime, timedelta, timezone

from fastapi import APIRouter, Depends, HTTPException, Query

from app.schemas.base import Success
from app.schemas.dashboard import RadiusLogRequest
from app.services.dashboard import (
    DashboardProxy,
    DashboardStatisticsService,
    get_dashboard_proxy,
    get_dashboard_statistics,
)
from app.services.health import DependencyHealth, get_redis_health
from app.services.nce import NCEClient, NCERadiusLogQuery, NCEUserQuery, get_nce_client
from app.settings import settings

router = APIRouter(tags=["WiFi运维"])


@router.get("/health", summary="查询外部服务健康状态")
async def get_external_service_health(
    nce_client: NCEClient = Depends(get_nce_client),
    redis_health: DependencyHealth = Depends(get_redis_health),
) -> Success:
    nce_health = await nce_client.health()
    return Success(
        data={
            "nce": nce_health.model_dump(mode="json"),
            "redis": redis_health.model_dump(mode="json"),
        }
    )


@router.get("/statistics", summary="查询 WiFi 每日认证统计")
async def get_daily_statistics(
    target_date: date | None = Query(default=None, alias="date"),
    statistics: DashboardStatisticsService = Depends(get_dashboard_statistics),
) -> Success:
    if not settings.NCE_MOCK_ENABLED and not settings.NCE_SITE_ID:
        raise HTTPException(status_code=503, detail="NCE_SITE_ID 尚未配置")
    china_today = (datetime.now(timezone.utc) + timedelta(hours=8)).date()
    result = await statistics.get_daily_statistics(target_date or china_today)
    return Success(data=result.model_dump(mode="json"))


@router.get("/online-users", summary="查询 NCE 实时在线用户")
async def get_online_users(
    user_name: str | None = Query(default=None, max_length=128),
    user_group_id: str | None = Query(default=None, max_length=64),
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=200),
    proxy: DashboardProxy = Depends(get_dashboard_proxy),
) -> Success:
    result = await proxy.query_online_users(
        NCEUserQuery(
            user_name=user_name,
            user_group_id=user_group_id,
            online_only=True,
            page=page,
            page_size=page_size,
        )
    )
    return Success(data=result.model_dump(mode="json"))


@router.post("/radius-logs", summary="查询 NCE RADIUS 准入日志")
async def get_radius_logs(
    request: RadiusLogRequest,
    proxy: DashboardProxy = Depends(get_dashboard_proxy),
) -> Success:
    site_id = settings.NCE_SITE_ID or ("mock-site" if settings.NCE_MOCK_ENABLED else None)
    if site_id is None:
        raise HTTPException(status_code=503, detail="NCE_SITE_ID 尚未配置")
    query = NCERadiusLogQuery(site_id=site_id, **request.model_dump())
    result = await proxy.query_radius_logs(query)
    return Success(data=result.model_dump(mode="json"))
