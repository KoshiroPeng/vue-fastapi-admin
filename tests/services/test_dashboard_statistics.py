from datetime import date

import pytest

from app.services.dashboard.statistics import DashboardStatisticsService
from app.services.nce.mock import MockNCEClient


@pytest.mark.asyncio
async def test_statistics_aggregate_mock_nce_without_persisting_passenger_rows() -> None:
    statistics = await DashboardStatisticsService(MockNCEClient()).get_daily_statistics(date(2026, 9, 10))

    assert statistics.total_authentications == 4
    assert statistics.success_count == 2
    assert statistics.failure_count == 2
    assert statistics.success_rate == 50.0
    assert statistics.online_users == 3
    assert statistics.method_distribution == {
        "sms": 1,
        "wechat": 1,
        "kiosk": 1,
        "boarding_pass": 1,
    }
    assert statistics.failure_reasons == {116: 1, 642: 1}
    assert sum(point.total for point in statistics.hourly_trend) == 4
    assert statistics.average_auth_duration_ms is None
