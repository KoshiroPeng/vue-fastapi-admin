from fastapi import APIRouter

from app.schemas.base import Success
from app.services.runtime_config import build_runtime_config_summary
from app.settings import settings

router = APIRouter(tags=["WiFi运维"])


@router.get("/summary", summary="查询脱敏运行配置摘要")
async def get_runtime_config_summary() -> Success:
    summary = build_runtime_config_summary(settings)
    return Success(data=summary.model_dump(mode="json"))
