from datetime import datetime, timezone

import pytest
from tortoise import Tortoise

from app.core.bgtask import BgTasks
from app.models.wifi import WifiExternalCallLog
from app.services.external_call_log import ExternalCallLogService, ExternalCallSummary


@pytest.mark.asyncio
async def test_external_call_log_persists_only_safe_summary() -> None:
    await Tortoise.init(db_url="sqlite://:memory:", modules={"models": ["app.models.wifi"]})
    await Tortoise.generate_schemas()
    try:
        service = ExternalCallLogService("test-pii-secret")
        row = await service.record(
            ExternalCallSummary(
                trace_id="trace-001",
                auth_tx_id="tx-sensitive-001",
                system_name="NCE",
                api_name="create_guest",
                method="POST",
                result_code="0",
                success=True,
                duration_ms=12,
            )
        )

        assert row.auth_tx_id_hash != "tx-sensitive-001"
        assert len(row.auth_tx_id_hash) == 64
        assert row.error_message_masked is None
        assert "tx-sensitive-001" not in str(await row.to_dict())

        await BgTasks.init_bg_tasks_obj()
        scheduled = await service.record_later(
            ExternalCallSummary(
                trace_id="trace-002",
                system_name="OCR",
                api_name="recognize_passport",
                method="POST",
                success=False,
                duration_ms=4000,
                error_category="TIMEOUT",
            )
        )
        assert scheduled is True
        assert await WifiExternalCallLog.all().count() == 1
        await BgTasks.execute_tasks()
        assert await WifiExternalCallLog.all().count() == 2
        assert await service.cleanup(30, datetime.now(timezone.utc)) == 0
    finally:
        await Tortoise.close_connections()
