from unittest.mock import AsyncMock

import pytest

from app.controllers.user import user_controller
from app.core.init_app import init_superuser
from app.settings import settings


@pytest.mark.asyncio
async def test_admin_bootstrap_is_disabled_by_default(monkeypatch: pytest.MonkeyPatch) -> None:
    exists = AsyncMock(return_value=False)
    create_user = AsyncMock()
    monkeypatch.setattr(user_controller.model, "exists", exists)
    monkeypatch.setattr(user_controller, "create_user", create_user)
    monkeypatch.setattr(settings, "BOOTSTRAP_ADMIN_ENABLED", False)

    await init_superuser()

    create_user.assert_not_awaited()


@pytest.mark.asyncio
async def test_admin_bootstrap_uses_injected_password(monkeypatch: pytest.MonkeyPatch) -> None:
    exists = AsyncMock(return_value=False)
    create_user = AsyncMock()
    monkeypatch.setattr(user_controller.model, "exists", exists)
    monkeypatch.setattr(user_controller, "create_user", create_user)
    monkeypatch.setattr(settings, "BOOTSTRAP_ADMIN_ENABLED", True)
    monkeypatch.setattr(settings, "BOOTSTRAP_ADMIN_PASSWORD", "Injected-Strong-Password-2026")

    await init_superuser()

    created = create_user.await_args.args[0]
    assert created.password == "Injected-Strong-Password-2026"
    assert created.password != "123456"
