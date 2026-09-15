from datetime import datetime, timedelta
from enum import Enum
from typing import Literal, Protocol

from pydantic import BaseModel, ConfigDict, Field, SecretStr, field_validator, model_validator

from app.core.masking import normalize_mac


class NCEHealthStatus(str, Enum):
    HEALTHY = "healthy"
    DEGRADED = "degraded"
    DOWN = "down"


class NCEHealth(BaseModel):
    model_config = ConfigDict(frozen=True)

    status: NCEHealthStatus
    mode: str
    configured: bool
    latency_ms: int = Field(ge=0)
    message: str


class NCEAccessToken(BaseModel):
    model_config = ConfigDict(frozen=True)

    value: SecretStr
    expires_at: datetime


class NCEGuestCreateRequest(BaseModel):
    model_config = ConfigDict(frozen=True)

    request_id: str = Field(min_length=1, max_length=64)
    username_prefix: str = Field(pattern=r"^[a-z][a-z0-9_]{1,15}$")
    valid_duration_minutes: int = Field(gt=0, le=10080)
    max_devices: int = Field(gt=0, le=10)
    description: str = Field(min_length=1, max_length=128)
    terminal_mac: str | None = Field(default=None, max_length=32)

    @field_validator("terminal_mac")
    @classmethod
    def normalize_bound_terminal_mac(cls, value: str | None) -> str | None:
        return normalize_mac(value) if value else None


class NCEGuest(BaseModel):
    model_config = ConfigDict(frozen=True)

    username: str
    password: SecretStr
    valid_until: datetime
    max_devices: int


class NCEAuthorizationStatus(str, Enum):
    PENDING = "pending"
    SUCCESS = "success"
    FAILED = "failed"


class NCETerminalAuthorizationRequest(BaseModel):
    model_config = ConfigDict(frozen=True)

    request_id: str = Field(min_length=1, max_length=64)
    username: str = Field(min_length=1, max_length=128)
    client_ip: str = Field(min_length=2, max_length=64)
    client_mac: str = Field(max_length=32)
    ssid: str = Field(min_length=1, max_length=64)
    device_mac: str | None = Field(default=None, max_length=32)
    device_esn: str | None = Field(default=None, max_length=128)
    ap_mac: str | None = Field(default=None, max_length=32)
    node_ip: str | None = Field(default=None, max_length=64)
    policy_name: str | None = Field(default=None, max_length=128)
    permit_seconds: int | None = Field(default=None, ge=0, le=360000)
    third_auth_type: int = Field(default=7, ge=1, le=7)

    @field_validator("client_mac", "device_mac", "ap_mac")
    @classmethod
    def normalize_authorization_mac(cls, value: str | None) -> str | None:
        return normalize_mac(value) if value else None

    @model_validator(mode="after")
    def validate_haca_context(self) -> "NCETerminalAuthorizationRequest":
        from ipaddress import ip_address

        try:
            ip_address(self.client_ip)
        except ValueError as exc:
            raise ValueError("终端 IP 地址无效") from exc
        if not self.device_mac and not self.device_esn:
            raise ValueError("认证设备 MAC 和 ESN 至少提供一个")
        if self.node_ip:
            try:
                if ip_address(self.node_ip).version != 4:
                    raise ValueError
            except ValueError as exc:
                raise ValueError("授权节点必须是有效 IPv4 地址") from exc
        return self


class NCEAuthorizationResult(BaseModel):
    model_config = ConfigDict(frozen=True)

    session_id: str = Field(min_length=1, max_length=128)
    status: NCEAuthorizationStatus
    result_code: str = Field(min_length=1, max_length=64)


class NCEUserQuery(BaseModel):
    model_config = ConfigDict(frozen=True)

    user_name: str | None = Field(default=None, max_length=128)
    user_group_id: str | None = Field(default=None, max_length=64)
    online_only: bool = False
    page: int = Field(default=1, ge=1)
    page_size: int = Field(default=20, ge=1, le=200)


class NCEUser(BaseModel):
    model_config = ConfigDict(frozen=True)

    id: str
    user_name: str
    user_group_id: str
    user_group_name: str
    user_type_code: int
    is_online: bool
    terminal_ip: str | None = None
    terminal_mac: str | None = None
    access_ssid: str | None = None
    connected_at: datetime | None = None


class NCEUserPage(BaseModel):
    model_config = ConfigDict(frozen=True)

    items: list[NCEUser]
    total: int = Field(ge=0)
    page: int = Field(ge=1)
    page_size: int = Field(ge=1)


class NCERadiusLogQuery(BaseModel):
    model_config = ConfigDict(frozen=True)

    site_id: str = Field(min_length=1, max_length=64)
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
    def validate_time_range(self) -> "NCERadiusLogQuery":
        if self.start_time.tzinfo is None or self.end_time.tzinfo is None:
            raise ValueError("RADIUS 查询时间必须包含时区")
        if self.end_time <= self.start_time:
            raise ValueError("RADIUS 查询结束时间必须晚于开始时间")
        if self.end_time - self.start_time > timedelta(days=7):
            raise ValueError("RADIUS 查询时间跨度不能超过 7 天")
        return self


class NCERadiusLog(BaseModel):
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


class NCERadiusLogPage(BaseModel):
    model_config = ConfigDict(frozen=True)

    items: list[NCERadiusLog]
    next_cursor: str | None = None
    page_size: int = Field(ge=1, le=101)


class NCEClient(Protocol):
    async def health(self) -> NCEHealth:
        """Return a side-effect-free dependency health snapshot."""

    async def get_access_token(self) -> NCEAccessToken:
        """Return a short-lived token without exposing it through repr/logging."""

    async def create_guest(self, request: NCEGuestCreateRequest) -> NCEGuest:
        """Create a temporary NCE guest through the selected adapter."""

    async def authorize_terminal(self, request: NCETerminalAuthorizationRequest) -> NCEAuthorizationResult:
        """Submit one HACA terminal authorization request."""

    async def query_authorization_result(
        self,
        session_id: str,
        node_ip: str | None = None,
    ) -> NCEAuthorizationResult:
        """Query the HACA authorization result by NCE session ID."""

    async def disconnect_terminal(self, request: NCETerminalAuthorizationRequest, session_id: str) -> None:
        """Force an authorized HACA terminal offline when the feature is enabled."""

    async def query_users(self, query: NCEUserQuery) -> NCEUserPage:
        """Query users or online terminals without local persistence."""

    async def query_radius_logs(self, query: NCERadiusLogQuery) -> NCERadiusLogPage:
        """Query one cursor page of RADIUS authentication logs."""
