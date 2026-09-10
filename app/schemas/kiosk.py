from datetime import datetime
from enum import Enum

from pydantic import BaseModel, ConfigDict, Field


class KioskIdType(str, Enum):
    ID_CARD = "ID_CARD"
    PASSPORT = "PASSPORT"


class KioskCreateGuestRequest(BaseModel):
    model_config = ConfigDict(populate_by_name=True, extra="forbid")

    id_type: KioskIdType = Field(alias="idType")
    id_digest: str = Field(alias="idDigest", pattern=r"^[0-9a-f]{64}$")


class KioskGuestResponse(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    username: str
    password: str
    valid_duration_minutes: int = Field(alias="validDurationMinutes")
    expire_time: datetime = Field(alias="expireTime")
    max_devices: int = Field(alias="maxDevices")
    ssid: str
