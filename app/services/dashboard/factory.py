from fastapi import Depends

from app.core.redis import redis_manager
from app.services.nce import NCEClient, get_nce_client
from app.settings import settings

from .cache import RedisQueryCache
from .proxy import DashboardProxy
from .statistics import DashboardStatisticsService


def _query_cache() -> RedisQueryCache:
    return RedisQueryCache(redis_manager.client)


def get_dashboard_proxy(nce_client: NCEClient = Depends(get_nce_client)) -> DashboardProxy:
    return DashboardProxy(
        nce_client=nce_client,
        cache=_query_cache(),
        online_cache_ttl_seconds=settings.DASHBOARD_ONLINE_CACHE_TTL_SECONDS,
        radius_cache_ttl_seconds=settings.DASHBOARD_RADIUS_CACHE_TTL_SECONDS,
    )


def get_dashboard_statistics(
    nce_client: NCEClient = Depends(get_nce_client),
) -> DashboardStatisticsService:
    site_id = settings.NCE_SITE_ID or ("mock-site" if settings.NCE_MOCK_ENABLED else "")
    return DashboardStatisticsService(
        nce_client=nce_client,
        cache=_query_cache(),
        site_id=site_id,
        cache_ttl_seconds=settings.DASHBOARD_STATISTICS_CACHE_TTL_SECONDS,
    )
