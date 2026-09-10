from datetime import datetime, timedelta
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from app.core.masking import normalize_mac


class OnlineUserItem(BaseModel):
    model_config = ConfigDict(frozen=True)

    id: str
    user_name: str
    user_group_name: str
    user_type_code: int
    terminal_ip: str | None = None
    terminal_mac: str | None = None
    access_ssid: str | None = None
    connected_at: datetime | None = None


class OnlineUserPage(BaseModel):
    model_config = ConfigDict(frozen=True)

    items: list[OnlineUserItem]
    total: int = Field(ge=0)
    page: int = Field(ge=1)
    page_size: int = Field(ge=1, le=200)


class HourlyTrendPoint(BaseModel):
    model_config = ConfigDict(frozen=True)

    hour: int = Field(ge=0, le=23)
    total: int = Field(ge=0)
    success: int = Field(ge=0)
    failure: int = Field(ge=0)


class DailyStatistics(BaseModel):
    model_config = ConfigDict(frozen=True)

    date: str
    total_authentications: int = Field(ge=0)
    success_count: int = Field(ge=0)
    failure_count: int = Field(ge=0)
    success_rate: float = Field(ge=0, le=100)
    online_users: int = Field(ge=0)
    average_auth_duration_ms: int | None = Field(default=None, ge=0)
    method_distribution: dict[str, int]
    failure_reasons: dict[int, int]
    hourly_trend: list[HourlyTrendPoint]


class RadiusLogRequest(BaseModel):
    model_config = ConfigDict(frozen=True)

    start_time: datetime
    end_time: datetime
    auth_result: Literal["success", "failure", "all"] = "all"
    user_name: str | None = Field(default=None, max_length=128)
    terminal_ip: str | None = Field(default=None, max_length=64)
    terminal_mac: str | None = Field(default=None, max_length=32)
    fail_reason_code: int | None = Field(default=None, ge=0)
    user_type_code: int | None = None
    auth_type_code: int | None = None
    page_size: int = Field(default=101, ge=1, le=101)
    cursor: str | None = Field(default=None, max_length=256)

    @field_validator("terminal_mac")
    @classmethod
    def normalize_terminal_mac(cls, value: str | None) -> str | None:
        return normalize_mac(value) if value else None

    @model_validator(mode="after")
    def validate_time_range(self) -> "RadiusLogRequest":
        if self.start_time.tzinfo is None or self.end_time.tzinfo is None:
            raise ValueError("RADIUS 查询时间必须包含时区")
        if self.end_time <= self.start_time:
            raise ValueError("RADIUS 查询结束时间必须晚于开始时间")
        if self.end_time - self.start_time > timedelta(days=7):
            raise ValueError("RADIUS 查询时间跨度不能超过 7 天")
        return self


class RadiusLogItem(BaseModel):
    model_config = ConfigDict(frozen=True)

    id: str
    user_name: str
    user_group_name: str
    user_type_code: int
    terminal_ip: str
    terminal_mac: str
    auth_type_code: int
    access_ssid: str
    authenticated_at: datetime
    auth_result_code: int
    fail_reason_code: int


class RadiusLogPage(BaseModel):
    model_config = ConfigDict(frozen=True)

    items: list[RadiusLogItem]
    next_cursor: str | None = None
    page_size: int = Field(ge=1, le=101)
