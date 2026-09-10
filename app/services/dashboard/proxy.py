from collections.abc import Callable

from app.core.masking import mask_account, mask_ip, mask_mac
from app.schemas.dashboard import OnlineUserItem, OnlineUserPage, RadiusLogItem, RadiusLogPage
from app.services.nce import NCEClient, NCERadiusLogQuery, NCEUserQuery

from .cache import RedisQueryCache


def _safe_mask(value: str | None, masker: Callable[[str], str]) -> str | None:
    if value is None:
        return None
    try:
        return masker(value)
    except ValueError:
        return "***"


class DashboardProxy:
    """Read-only NCE proxy that returns only management-safe, masked data."""

    def __init__(
        self,
        nce_client: NCEClient,
        cache: RedisQueryCache | None = None,
        online_cache_ttl_seconds: int = 5,
        radius_cache_ttl_seconds: int = 10,
    ) -> None:
        self._nce_client = nce_client
        self._cache = cache
        self._online_cache_ttl_seconds = online_cache_ttl_seconds
        self._radius_cache_ttl_seconds = radius_cache_ttl_seconds

    async def query_online_users(self, query: NCEUserQuery) -> OnlineUserPage:
        async def load() -> OnlineUserPage:
            source = await self._nce_client.query_users(query)
            return OnlineUserPage(
                items=[
                    OnlineUserItem(
                        id=item.id,
                        user_name=mask_account(item.user_name),
                        user_group_name=item.user_group_name,
                        user_type_code=item.user_type_code,
                        terminal_ip=_safe_mask(item.terminal_ip, mask_ip),
                        terminal_mac=_safe_mask(item.terminal_mac, mask_mac),
                        access_ssid=item.access_ssid,
                        connected_at=item.connected_at,
                    )
                    for item in source.items
                ],
                total=source.total,
                page=source.page,
                page_size=source.page_size,
            )

        if self._cache is None:
            return await load()
        return await self._cache.get_or_load(
            namespace="online-users",
            key_data=query.model_dump(mode="json"),
            ttl_seconds=self._online_cache_ttl_seconds,
            model=OnlineUserPage,
            loader=load,
        )

    async def query_radius_logs(self, query: NCERadiusLogQuery) -> RadiusLogPage:
        async def load() -> RadiusLogPage:
            source = await self._nce_client.query_radius_logs(query)
            return RadiusLogPage(
                items=[
                    RadiusLogItem(
                        id=item.id,
                        user_name=mask_account(item.user_name),
                        user_group_name=item.user_group_name,
                        user_type_code=item.user_type_code,
                        terminal_ip=_safe_mask(item.terminal_ip, mask_ip) or "***",
                        terminal_mac=_safe_mask(item.terminal_mac, mask_mac) or "***",
                        auth_type_code=item.auth_type_code,
                        access_ssid=item.access_ssid,
                        authenticated_at=item.authenticated_at,
                        auth_result_code=item.auth_result_code,
                        fail_reason_code=item.fail_reason_code,
                    )
                    for item in source.items
                ],
                next_cursor=source.next_cursor,
                page_size=source.page_size,
            )

        if self._cache is None:
            return await load()
        return await self._cache.get_or_load(
            namespace="radius-logs",
            key_data=query.model_dump(mode="json"),
            ttl_seconds=self._radius_cache_ttl_seconds,
            model=RadiusLogPage,
            loader=load,
        )
