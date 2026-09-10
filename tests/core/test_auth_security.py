import pytest
from fastapi import HTTPException

from app.core.dependency import AuthControl


@pytest.mark.asyncio
async def test_dev_token_is_not_an_authentication_bypass() -> None:
    with pytest.raises(HTTPException) as exc_info:
        await AuthControl.is_authed("dev")

    assert exc_info.value.status_code == 401
    assert "dev" not in str(exc_info.value.detail)
