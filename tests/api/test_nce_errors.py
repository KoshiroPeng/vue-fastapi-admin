import httpx
import pytest
from fastapi import FastAPI

from app.core.exceptions import NCEErrorHandle
from app.services.nce.errors import (
    NCEAuthenticationError,
    NCEBusinessError,
    NCEError,
    NCETimeoutError,
    NCEUnavailableError,
)


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("error", "status_code", "error_code"),
    [
        (NCEAuthenticationError("internal auth detail"), 502, "NCE_AUTHENTICATION_FAILED"),
        (NCEBusinessError("NCE-500", "internal business detail"), 502, "NCE_BUSINESS_ERROR"),
        (NCETimeoutError("internal timeout detail"), 504, "NCE_TIMEOUT"),
        (NCEUnavailableError("internal unavailable detail"), 502, "NCE_UNAVAILABLE"),
    ],
)
async def test_nce_errors_have_stable_safe_http_mapping(
    error: NCEError,
    status_code: int,
    error_code: str,
) -> None:
    app = FastAPI()
    app.add_exception_handler(NCEError, NCEErrorHandle)

    @app.get("/nce")
    async def call_nce() -> None:
        raise error

    async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://test") as client:
        response = await client.get("/nce")

    assert response.status_code == status_code
    assert response.json()["error_code"] == error_code
    assert "internal" not in response.text
