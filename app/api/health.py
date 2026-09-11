import asyncio

from fastapi import APIRouter
from starlette.responses import JSONResponse
from tortoise import Tortoise

from app.core.redis import redis_manager
from app.log import logger

router = APIRouter(tags=["Health"])


async def check_mysql() -> None:
    connection = Tortoise.get_connection("default")
    await connection.execute_query("SELECT 1")


async def check_redis() -> None:
    await redis_manager.client.ping()


@router.get("/health/live", include_in_schema=False)
async def liveness() -> dict[str, str]:
    return {"status": "alive"}


@router.get("/health/ready", include_in_schema=False)
async def readiness() -> JSONResponse:
    dependencies = ("mysql", "redis")
    results = await asyncio.gather(check_mysql(), check_redis(), return_exceptions=True)
    failed_dependencies = []
    for dependency, result in zip(dependencies, results, strict=True):
        if isinstance(result, BaseException):
            failed_dependencies.append(dependency)
            logger.warning(
                "event=readiness_check_failed dependency={} error_type={}",
                dependency,
                type(result).__name__,
            )

    if failed_dependencies:
        return JSONResponse(
            status_code=503,
            content={"status": "not_ready", "failed_dependencies": failed_dependencies},
        )
    return JSONResponse(status_code=200, content={"status": "ready"})
