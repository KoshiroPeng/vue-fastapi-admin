from datetime import datetime, timedelta, timezone

import pytest

from app.services.dashboard.proxy import DashboardProxy
from app.services.nce import NCERadiusLogQuery, NCEUserQuery
from app.services.nce.mock import MockNCEClient


@pytest.mark.asyncio
async def test_online_user_proxy_masks_all_terminal_identifiers() -> None:
    proxy = DashboardProxy(MockNCEClient())

    page = await proxy.query_online_users(NCEUserQuery(online_only=True, page=1, page_size=20))

    assert page.total == 3
    assert page.items[0].user_name == "sms_138****0001"
    assert page.items[0].terminal_ip == "10.***.***.8"
    assert page.items[0].terminal_mac == "AA:**:**:**:**:01"
    serialized = page.model_dump_json()
    assert "13800000001" not in serialized
    assert "AA-BB-CC-DD-EE-01" not in serialized


@pytest.mark.asyncio
async def test_radius_log_proxy_preserves_cursor_and_masks_rows() -> None:
    start = datetime(2026, 9, 10, 0, 0, tzinfo=timezone.utc)
    proxy = DashboardProxy(MockNCEClient())

    page = await proxy.query_radius_logs(
        NCERadiusLogQuery(
            site_id="mock-site",
            start_time=start,
            end_time=start + timedelta(days=1),
            page_size=2,
        )
    )

    assert len(page.items) == 2
    assert page.next_cursor is not None
    assert page.items[0].user_name == "sms_138****0001"
    assert page.items[0].terminal_ip == "10.***.***.8"
    assert page.items[0].terminal_mac == "AA:**:**:**:**:01"
    assert "13800000001" not in page.model_dump_json()
