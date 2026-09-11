from contextlib import asynccontextmanager

from fastapi import FastAPI
from tortoise import Tortoise

from app.api.health import router as health_router
from app.core.exceptions import SettingNotFound
from app.core.redis import redis_manager
from app.core.init_app import (
    init_db,
    make_middlewares,
    register_exceptions,
    register_routers,
)

try:
    from app.settings.config import settings
except ImportError:
    raise SettingNotFound("Can not import settings")


@asynccontextmanager
async def lifespan(app: FastAPI):
    await redis_manager.connect()
    try:
        await init_db()
        yield
    finally:
        await Tortoise.close_connections()
        await redis_manager.close()


def create_app() -> FastAPI:
    app = FastAPI(
        title=settings.APP_TITLE,
        description=settings.APP_DESCRIPTION,
        version=settings.VERSION,
        openapi_url="/openapi.json",
        middleware=make_middlewares(),
        lifespan=lifespan,
    )
    register_exceptions(app)
    app.include_router(health_router)
    register_routers(app, prefix="/api")
    return app


app = create_app()
