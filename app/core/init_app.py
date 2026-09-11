from datetime import datetime

from fastapi import FastAPI
from fastapi.middleware import Middleware
from fastapi.middleware.cors import CORSMiddleware
from tortoise import Tortoise
from app.api import api_router
from app.controllers.api import api_controller
from app.controllers.user import UserCreate, user_controller
from app.core.exceptions import (
    DoesNotExist,
    DoesNotExistHandle,
    HTTPException,
    HttpExcHandle,
    IntegrityError,
    IntegrityHandle,
    NCEErrorHandle,
    RequestValidationError,
    RequestValidationHandle,
    ResponseValidationError,
    ResponseValidationHandle,
    RiskControlHandle,
)
from app.core.wifi_menu import init_wifi_menus
from app.log import logger
from app.models.admin import Api, Menu, Role
from app.schemas.menus import MenuType
from app.services.external_call_log import ExternalCallLogService
from app.services.nce.errors import NCEError
from app.services.risk_control import RiskControlError
from app.settings.config import settings

from .middlewares import BackGroundTaskMiddleware, HttpAuditLogMiddleware
from .request_context import RequestContextMiddleware


def make_middlewares():
    middleware = [
        Middleware(RequestContextMiddleware),
        Middleware(
            CORSMiddleware,
            allow_origins=settings.CORS_ORIGINS,
            allow_credentials=settings.CORS_ALLOW_CREDENTIALS,
            allow_methods=settings.CORS_ALLOW_METHODS,
            allow_headers=settings.CORS_ALLOW_HEADERS,
        ),
        Middleware(BackGroundTaskMiddleware),
        Middleware(
            HttpAuditLogMiddleware,
            methods=["GET", "POST", "PUT", "DELETE"],
            exclude_paths=[
                "/api/v1/base/access_token",
                "/api/v1/kiosk/",
                "/api/v1/portal/",
                "/docs",
                "/openapi.json",
            ],
        ),
    ]
    return middleware


def register_exceptions(app: FastAPI):
    app.add_exception_handler(DoesNotExist, DoesNotExistHandle)
    app.add_exception_handler(HTTPException, HttpExcHandle)
    app.add_exception_handler(IntegrityError, IntegrityHandle)
    app.add_exception_handler(RequestValidationError, RequestValidationHandle)
    app.add_exception_handler(ResponseValidationError, ResponseValidationHandle)
    app.add_exception_handler(NCEError, NCEErrorHandle)
    app.add_exception_handler(RiskControlError, RiskControlHandle)


def register_routers(app: FastAPI, prefix: str = "/api"):
    app.include_router(api_router, prefix=prefix)


async def init_superuser():
    user = await user_controller.model.exists()
    if user:
        return
    if not settings.BOOTSTRAP_ADMIN_ENABLED:
        logger.warning("event=bootstrap_admin_skipped reason=disabled")
        return
    if not settings.BOOTSTRAP_ADMIN_PASSWORD:
        raise RuntimeError("BOOTSTRAP_ADMIN_ENABLED=true 时必须配置 BOOTSTRAP_ADMIN_PASSWORD")
    await user_controller.create_user(
        UserCreate(
            username=settings.BOOTSTRAP_ADMIN_USERNAME,
            email=settings.BOOTSTRAP_ADMIN_EMAIL,
            password=settings.BOOTSTRAP_ADMIN_PASSWORD,
            is_active=True,
            is_superuser=True,
        )
    )
    logger.info("event=bootstrap_admin_created username={}", settings.BOOTSTRAP_ADMIN_USERNAME)


async def init_menus():
    menus = await Menu.exists()
    if not menus:
        parent_menu = await Menu.create(
            menu_type=MenuType.CATALOG,
            name="系统管理",
            path="/system",
            order=1,
            parent_id=0,
            icon="carbon:gui-management",
            is_hidden=False,
            component="Layout",
            keepalive=False,
            redirect="/system/user",
        )
        children_menu = [
            Menu(
                menu_type=MenuType.MENU,
                name="用户管理",
                path="user",
                order=1,
                parent_id=parent_menu.id,
                icon="material-symbols:person-outline-rounded",
                is_hidden=False,
                component="/system/user",
                keepalive=False,
            ),
            Menu(
                menu_type=MenuType.MENU,
                name="角色管理",
                path="role",
                order=2,
                parent_id=parent_menu.id,
                icon="carbon:user-role",
                is_hidden=False,
                component="/system/role",
                keepalive=False,
            ),
            Menu(
                menu_type=MenuType.MENU,
                name="菜单管理",
                path="menu",
                order=3,
                parent_id=parent_menu.id,
                icon="material-symbols:list-alt-outline",
                is_hidden=False,
                component="/system/menu",
                keepalive=False,
            ),
            Menu(
                menu_type=MenuType.MENU,
                name="API管理",
                path="api",
                order=4,
                parent_id=parent_menu.id,
                icon="ant-design:api-outlined",
                is_hidden=False,
                component="/system/api",
                keepalive=False,
            ),
            Menu(
                menu_type=MenuType.MENU,
                name="部门管理",
                path="dept",
                order=5,
                parent_id=parent_menu.id,
                icon="mingcute:department-line",
                is_hidden=False,
                component="/system/dept",
                keepalive=False,
            ),
            Menu(
                menu_type=MenuType.MENU,
                name="审计日志",
                path="auditlog",
                order=6,
                parent_id=parent_menu.id,
                icon="ph:clipboard-text-bold",
                is_hidden=False,
                component="/system/auditlog",
                keepalive=False,
            ),
        ]
        await Menu.bulk_create(children_menu)
        await Menu.create(
            menu_type=MenuType.MENU,
            name="一级菜单",
            path="/top-menu",
            order=2,
            parent_id=0,
            icon="material-symbols:featured-play-list-outline",
            is_hidden=False,
            component="/top-menu",
            keepalive=False,
            redirect="",
        )

    await init_wifi_menus()


async def init_apis():
    await api_controller.refresh_api()


async def init_db():
    await Tortoise.init(config=settings.TORTOISE_ORM)


async def init_roles():
    admin_role, _ = await Role.get_or_create(name="管理员", defaults={"desc": "管理员角色"})
    user_role, user_created = await Role.get_or_create(name="普通用户", defaults={"desc": "普通用户角色"})

    # 管理员角色在每次启动时同步新增菜单和 API；普通角色不自动获得 WiFi 权限。
    all_apis = await Api.all()
    all_menus = await Menu.all()
    await admin_role.apis.add(*all_apis)
    await admin_role.menus.add(*all_menus)

    if user_created:
        basic_apis = await Api.filter(tags="基础模块")
        await user_role.apis.add(*basic_apis)


async def init_data():
    await init_db()
    if settings.PII_HASH_SECRET:
        deleted = await ExternalCallLogService(settings.PII_HASH_SECRET).cleanup(
            settings.EXTERNAL_CALL_LOG_RETENTION_DAYS,
            datetime.now(),
        )
        if deleted:
            logger.info("event=external_call_log_cleanup deleted={}", deleted)
    await init_superuser()
    await init_menus()
    await init_apis()
    await init_roles()
