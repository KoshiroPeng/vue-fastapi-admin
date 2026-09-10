from fastapi.exceptions import (
    HTTPException,
    RequestValidationError,
    ResponseValidationError,
)
from fastapi.requests import Request
from fastapi.responses import JSONResponse
from tortoise.exceptions import DoesNotExist, IntegrityError

from app.log import logger
from app.services.risk_control import RateLimitExceeded, RiskControlError


class SettingNotFound(Exception):
    pass


async def DoesNotExistHandle(req: Request, exc: DoesNotExist) -> JSONResponse:
    content = dict(
        code=404,
        msg=f"Object has not found, exc: {exc}, query_params: {req.query_params}",
    )
    return JSONResponse(content=content, status_code=404)


async def IntegrityHandle(_: Request, exc: IntegrityError) -> JSONResponse:
    content = dict(
        code=500,
        msg=f"IntegrityError，{exc}",
    )
    return JSONResponse(content=content, status_code=500)


async def HttpExcHandle(_: Request, exc: HTTPException) -> JSONResponse:
    content = dict(code=exc.status_code, msg=exc.detail, data=None)
    return JSONResponse(content=content, status_code=exc.status_code)


async def RequestValidationHandle(_: Request, exc: RequestValidationError) -> JSONResponse:
    safe_errors = [
        {"type": error.get("type"), "loc": list(error.get("loc", ())), "msg": error.get("msg")}
        for error in exc.errors()
    ]
    content = {
        "code": 422,
        "msg": "请求参数校验失败",
        "data": {"errors": safe_errors},
        "error_code": "REQUEST_INVALID",
    }
    return JSONResponse(content=content, status_code=422)


async def ResponseValidationHandle(_: Request, exc: ResponseValidationError) -> JSONResponse:
    content = dict(code=500, msg=f"ResponseValidationError, {exc}")
    return JSONResponse(content=content, status_code=500)


async def RiskControlHandle(req: Request, exc: RiskControlError) -> JSONResponse:
    logger.warning(
        "event=risk_control_rejected path={} error_code={} status_code={}",
        req.url.path,
        exc.error_code,
        exc.status_code,
    )
    headers = None
    if isinstance(exc, RateLimitExceeded):
        headers = {"Retry-After": str(exc.retry_after_seconds)}
    content = {
        "code": exc.status_code,
        "msg": exc.public_message,
        "data": None,
        "error_code": exc.error_code,
    }
    return JSONResponse(content=content, status_code=exc.status_code, headers=headers)
