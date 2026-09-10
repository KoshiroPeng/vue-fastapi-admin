from datetime import date

from pydantic import BaseModel, ConfigDict, Field, field_validator

from app.core.masking import normalize_mac


class PortalClientContext(BaseModel):
    model_config = ConfigDict(populate_by_name=True, extra="forbid")

    client_ip: str = Field(alias="clientIp", max_length=64)
    client_mac: str = Field(alias="clientMac", max_length=32)
    ssid: str | None = Field(default=None, max_length=64)

    @field_validator("client_mac")
    @classmethod
    def validate_mac(cls, value: str) -> str:
        return normalize_mac(value)


class BoardingPassPortalRequest(PortalClientContext):
    flight_date: date = Field(alias="flightDate")
    flight_no: str = Field(alias="flightNo", pattern=r"^[A-Za-z0-9]{2,3}\d{3,4}$")
    seat_no: str = Field(alias="seatNo", pattern=r"^\d{1,2}[A-Za-z]$")
    document_last4: str = Field(alias="documentLast4", pattern=r"^[A-Za-z0-9]{4}$")

    @field_validator("flight_no", "seat_no", mode="before")
    @classmethod
    def normalize_uppercase(cls, value: str) -> str:
        return value.replace(" ", "").upper() if isinstance(value, str) else value


class WeChatStartRequest(PortalClientContext):
    pass


class WeChatCallbackRequest(BaseModel):
    model_config = ConfigDict(populate_by_name=True, extra="forbid")

    auth_tx_id: str = Field(alias="authTxId", min_length=1, max_length=64)
    result: str = Field(pattern=r"^(SUCCESS|FAILED)$")
    nce_success: bool = Field(alias="nceSuccess")
