from fastapi import FastAPI
from fastapi.middleware import Middleware
from fastapi.middleware.cors import CORSMiddleware
from tortoise import Tortoise
from app.api import api_router
from app.api.mini_program import router as mini_program_router
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
                "/secoWS/service/NewGuestManagerServices",
                "/PortalServer/AppPortalAuth",
                "/docs",
                "/openapi.json",
                "/health/live",
                "/health/ready",
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
    app.include_router(mini_program_router)


async def init_db():
    await Tortoise.init(config=settings.TORTOISE_ORM)
