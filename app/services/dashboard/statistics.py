import asyncio
from collections import Counter
from datetime import date, datetime, time, timedelta, timezone

from app.schemas.dashboard import DailyStatistics, HourlyTrendPoint
from app.services.nce import NCEBusinessError, NCEClient, NCERadiusLog, NCERadiusLogQuery, NCEUserQuery

from .cache import RedisQueryCache

_SHANGHAI = timezone(timedelta(hours=8), "Asia/Shanghai")


class DashboardStatisticsService:
    def __init__(
        self,
        nce_client: NCEClient,
        cache: RedisQueryCache | None = None,
        site_id: str = "mock-site",
        cache_ttl_seconds: int = 30,
    ) -> None:
        self._nce_client = nce_client
        self._cache = cache
        self._site_id = site_id
        self._cache_ttl_seconds = cache_ttl_seconds

    async def get_daily_statistics(self, target_date: date) -> DailyStatistics:
        async def load() -> DailyStatistics:
            start = datetime.combine(target_date, time.min, tzinfo=_SHANGHAI)
            end = datetime.combine(target_date, time.max, tzinfo=_SHANGHAI)
            online_task = asyncio.create_task(
                self._nce_client.query_users(NCEUserQuery(online_only=True, page=1, page_size=1))
            )
            logs = await self._load_all_logs(start, end)
            online = await online_task
            success_count = sum(item.auth_result_code == 0 for item in logs)
            failure_count = len(logs) - success_count
            method_distribution = Counter(self._auth_method(item) for item in logs)
            failure_reasons = Counter(item.fail_reason_code for item in logs if item.auth_result_code != 0)
            hourly = []
            for hour in range(24):
                hour_logs = [item for item in logs if item.authenticated_at.astimezone(_SHANGHAI).hour == hour]
                hourly_success = sum(item.auth_result_code == 0 for item in hour_logs)
                hourly.append(
                    HourlyTrendPoint(
                        hour=hour,
                        total=len(hour_logs),
                        success=hourly_success,
                        failure=len(hour_logs) - hourly_success,
                    )
                )
            total = len(logs)
            return DailyStatistics(
                date=target_date.isoformat(),
                total_authentications=total,
                success_count=success_count,
                failure_count=failure_count,
                success_rate=round(success_count * 100 / total, 2) if total else 0,
                online_users=online.total,
                average_auth_duration_ms=None,
                method_distribution=dict(method_distribution),
                failure_reasons=dict(failure_reasons),
                hourly_trend=hourly,
            )

        if self._cache is None:
            return await load()
        return await self._cache.get_or_load(
            namespace="daily-statistics",
            key_data={"date": target_date.isoformat(), "site_id": self._site_id},
            ttl_seconds=self._cache_ttl_seconds,
            model=DailyStatistics,
            loader=load,
        )

    async def _load_all_logs(self, start: datetime, end: datetime) -> list[NCERadiusLog]:
        items: list[NCERadiusLog] = []
        cursor = None
        seen_cursors: set[str] = set()
        for _ in range(100):
            page = await self._nce_client.query_radius_logs(
                NCERadiusLogQuery(
                    site_id=self._site_id,
                    start_time=start,
                    end_time=end,
                    page_size=101,
                    cursor=cursor,
                )
            )
            items.extend(page.items)
            if page.next_cursor is None:
                return items
            if page.next_cursor in seen_cursors:
                raise NCEBusinessError("NCE_CURSOR_LOOP", "NCE RADIUS 游标重复")
            seen_cursors.add(page.next_cursor)
            cursor = page.next_cursor
        raise NCEBusinessError("NCE_PAGE_LIMIT", "NCE RADIUS 查询超过安全分页上限")

    @staticmethod
    def _auth_method(item: NCERadiusLog) -> str:
        if item.user_type_code == 1:
            return "sms"
        if item.user_type_code == 5:
            return "wechat"
        name = item.user_name.casefold()
        if name.startswith("kiosk_"):
            return "kiosk"
        if name.startswith("bp_"):
            return "boarding_pass"
        if name.startswith("pass_"):
            return "passport"
        return "guest"
