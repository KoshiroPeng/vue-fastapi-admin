from datetime import datetime, timedelta
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator


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


class RadiusLogRequest(BaseModel):
    model_config = ConfigDict(frozen=True)

    start_time: datetime
    end_time: datetime
    auth_result: Literal["success", "failure", "all"] = "all"
    fail_reason_code: int | None = Field(default=None, ge=0)
    user_type_code: int | None = None
    auth_type_code: int | None = None
    page_size: int = Field(default=101, ge=1, le=101)
    cursor: str | None = Field(default=None, max_length=256)

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
