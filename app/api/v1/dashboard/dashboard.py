from fastapi import APIRouter, Depends

from app.schemas.base import Success
from app.services.nce import NCEClient, get_nce_client

router = APIRouter(tags=["WiFi运维"])


@router.get("/health", summary="查询外部服务健康状态")
async def get_external_service_health(nce_client: NCEClient = Depends(get_nce_client)) -> Success:
    nce_health = await nce_client.health()
    return Success(data={"nce": nce_health.model_dump(mode="json")})
