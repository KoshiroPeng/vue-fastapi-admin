from fastapi import Depends

from app.core.redis import redis_manager
from app.services.nce import NCEClient, get_nce_client
from app.settings import settings

from .cache import RedisQueryCache
from .proxy import DashboardProxy


def get_dashboard_proxy(nce_client: NCEClient = Depends(get_nce_client)) -> DashboardProxy:
    return DashboardProxy(
        nce_client=nce_client,
        cache=RedisQueryCache(redis_manager.client),
        online_cache_ttl_seconds=settings.DASHBOARD_ONLINE_CACHE_TTL_SECONDS,
        radius_cache_ttl_seconds=settings.DASHBOARD_RADIUS_CACHE_TTL_SECONDS,
    )
