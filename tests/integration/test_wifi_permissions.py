import pytest
from tortoise import Tortoise

from app.core.init_app import init_roles
from app.core.wifi_menu import init_wifi_menus
from app.models.admin import Api, Menu, Role
from app.models.enums import MethodType


@pytest.mark.asyncio
async def test_wifi_menu_initialization_is_idempotent_and_admin_only() -> None:
    await Tortoise.init(db_url="sqlite://:memory:", modules={"models": ["app.models.admin"]})
    await Tortoise.generate_schemas()
    try:
        await Api.create(
            path="/api/v1/dashboard/statistics",
            method=MethodType.GET,
            summary="统计",
            tags="WiFi运维",
        )
        await Api.create(
            path="/api/v1/base/userinfo",
            method=MethodType.GET,
            summary="用户信息",
            tags="基础模块",
        )

        first = await init_wifi_menus()
        second = await init_wifi_menus()
        await init_roles()

        assert len(first) == 8
        assert len(second) == 8
        assert await Menu.filter(path__startswith="/wifi").count() == 8
        admin_role = await Role.get(name="管理员")
        user_role = await Role.get(name="普通用户")
        assert await admin_role.menus.filter(path="/wifi/statistics").exists()
        assert await admin_role.apis.filter(path="/api/v1/dashboard/statistics").exists()
        assert not await user_role.menus.filter(path__startswith="/wifi").exists()
        assert not await user_role.apis.filter(path="/api/v1/dashboard/statistics").exists()
    finally:
        await Tortoise.close_connections()
