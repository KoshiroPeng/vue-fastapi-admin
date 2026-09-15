from datetime import datetime
from typing import Literal, Protocol

from pydantic import BaseModel, ConfigDict, Field, SecretStr, model_validator


class PassportImage(BaseModel):
    model_config = ConfigDict(frozen=True)

    content: bytes = Field(repr=False, exclude=True, min_length=4, max_length=4 * 1024 * 1024)
    content_type: Literal["image/jpeg", "image/png"]

    @model_validator(mode="after")
    def validate_magic(self) -> "PassportImage":
        jpeg = self.content_type == "image/jpeg" and self.content.startswith(b"\xff\xd8\xff")
        png = self.content_type == "image/png" and self.content.startswith(b"\x89PNG\r\n\x1a\n")
        if not jpeg and not png:
            raise ValueError("图片 MIME 与文件头不一致")
        return self


class PassportOCRResult(BaseModel):
    model_config = ConfigDict(frozen=True)

    passport_number: SecretStr
    mrz_valid: bool
    result_code: str


class PassportAuthResult(BaseModel):
    model_config = ConfigDict(frozen=True)

    auth_tx_id: str
    username: str
    password: SecretStr
    passport_number_masked: str
    valid_until: datetime
    authorization_session_id: str


class PassportOCRRejected(Exception):
    pass


class PassportOCRClient(Protocol):
    async def recognize(self, image: PassportImage) -> PassportOCRResult:
        """Recognize an in-memory image without writing it to disk."""
