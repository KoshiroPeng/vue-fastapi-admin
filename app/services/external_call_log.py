import hashlib
import hmac
import secrets
from datetime import datetime, timedelta

from pydantic import BaseModel, ConfigDict, Field

from app.core.bgtask import BgTasks
from app.models.wifi import WifiExternalCallLog


class ExternalCallSummary(BaseModel):
    model_config = ConfigDict(frozen=True)

    trace_id: str = Field(min_length=1, max_length=64)
    auth_tx_id: str | None = Field(default=None, max_length=64)
    system_name: str = Field(pattern=r"^[A-Z][A-Z0-9_-]{1,31}$")
    api_name: str = Field(min_length=1, max_length=128)
    method: str = Field(pattern=r"^(GET|POST|PUT|PATCH|DELETE)$")
    result_code: str | None = Field(default=None, max_length=32)
    success: bool
    duration_ms: int = Field(ge=0)
    error_category: str | None = Field(default=None, pattern=r"^[A-Z][A-Z0-9_:-]{1,63}$")


class ExternalCallLogService:
    def __init__(self, pii_hash_secret: str) -> None:
        if not pii_hash_secret:
            raise ValueError("PII_HASH_SECRET 尚未配置")
        self._secret = pii_hash_secret.encode("utf-8")

    async def record(self, summary: ExternalCallSummary) -> WifiExternalCallLog:
        auth_tx_hash = None
        if summary.auth_tx_id:
            auth_tx_hash = hmac.new(self._secret, summary.auth_tx_id.encode("utf-8"), hashlib.sha256).hexdigest()
        return await WifiExternalCallLog.create(
            trace_id=summary.trace_id,
            auth_tx_id_hash=auth_tx_hash,
            system_name=summary.system_name,
            api_name=summary.api_name,
            method=summary.method,
            result_code=summary.result_code,
            success=summary.success,
            duration_ms=summary.duration_ms,
            error_message_masked=summary.error_category,
        )

    async def record_later(self, summary: ExternalCallSummary, sample_rate: float = 1.0) -> bool:
        if not 0 <= sample_rate <= 1:
            raise ValueError("sample_rate 必须在 0 到 1 之间")
        if sample_rate < 1 and secrets.randbelow(10_000) >= int(sample_rate * 10_000):
            return False
        await BgTasks.add_task(self.record, summary)
        return True

    async def cleanup(self, retention_days: int, now: datetime) -> int:
        if not 7 <= retention_days <= 365:
            raise ValueError("日志保留期必须在 7 到 365 天之间")
        return await WifiExternalCallLog.filter(created_at__lt=now - timedelta(days=retention_days)).delete()
