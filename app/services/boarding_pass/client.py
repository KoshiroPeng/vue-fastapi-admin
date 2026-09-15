from datetime import date, datetime
from typing import Protocol

from pydantic import BaseModel, ConfigDict, Field, SecretStr, field_validator

from app.core.masking import normalize_mac


class BoardingPassAuthRequest(BaseModel):
    model_config = ConfigDict(frozen=True)

    flight_date: date
    flight_no: str = Field(pattern=r"^[A-Za-z0-9]{2,3}\d{3,4}$")
    seat_no: str = Field(pattern=r"^\d{1,2}[A-Za-z]$")
    document_last4: str = Field(pattern=r"^[A-Za-z0-9]{4}$")
    client_ip: str
    client_mac: str
    ssid: str | None = Field(default=None, max_length=64)
    device_mac: str | None = Field(default=None, max_length=32)
    device_esn: str | None = Field(default=None, max_length=128)
    ap_mac: str | None = Field(default=None, max_length=32)
    node_ip: str | None = Field(default=None, max_length=64)

    @field_validator("flight_no", "seat_no", mode="before")
    @classmethod
    def normalize_uppercase(cls, value: str) -> str:
        return value.replace(" ", "").upper() if isinstance(value, str) else value

    @field_validator("client_mac", "device_mac", "ap_mac")
    @classmethod
    def validate_mac(cls, value: str | None) -> str | None:
        return normalize_mac(value) if value else None


class BoardingPassVerification(BaseModel):
    model_config = ConfigDict(frozen=True)

    verified: bool
    result_code: str
    valid_until: datetime | None = None


class BoardingPassAuthResult(BaseModel):
    model_config = ConfigDict(frozen=True)

    auth_tx_id: str
    username: str
    password: SecretStr
    valid_until: datetime
    authorization_session_id: str


class BoardingPassRejected(Exception):
    pass


class BoardingPassClient(Protocol):
    async def verify(self, request: BoardingPassAuthRequest) -> BoardingPassVerification:
        """Verify all three boarding factors as one indivisible match."""
