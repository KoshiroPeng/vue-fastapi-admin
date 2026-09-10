from datetime import datetime
from enum import Enum

from pydantic import BaseModel, ConfigDict, Field


class AuthMethod(str, Enum):
    SMS = "SMS"
    WECHAT = "WECHAT"
    BOARDING_PASS = "BOARDING_PASS"
    PASSPORT = "PASSPORT"
    KIOSK = "KIOSK"


class AuthStatus(str, Enum):
    INIT = "INIT"
    PENDING = "PENDING"
    SUCCESS = "SUCCESS"
    FAILED = "FAILED"
    EXPIRED = "EXPIRED"


_ALLOWED_TRANSITIONS = {
    AuthStatus.INIT: {AuthStatus.PENDING, AuthStatus.FAILED},
    AuthStatus.PENDING: {AuthStatus.SUCCESS, AuthStatus.FAILED},
    AuthStatus.SUCCESS: set(),
    AuthStatus.FAILED: set(),
    AuthStatus.EXPIRED: set(),
}


def is_transition_allowed(current: AuthStatus, target: AuthStatus) -> bool:
    return target in _ALLOWED_TRANSITIONS[current]


class AuthTransaction(BaseModel):
    model_config = ConfigDict(frozen=True)

    auth_tx_id: str = Field(min_length=1, max_length=64)
    auth_method: AuthMethod
    status: AuthStatus
    client_ip_hash: str = Field(pattern=r"^[0-9a-f]{64}$")
    client_mac_hash: str = Field(pattern=r"^[0-9a-f]{64}$")
    ssid: str | None = Field(default=None, max_length=64)
    expire_at: datetime
    trace_id: str = Field(min_length=1, max_length=64)
    consumed_at: datetime | None = None
