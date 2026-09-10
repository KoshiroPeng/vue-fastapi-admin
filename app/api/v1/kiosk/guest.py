from fastapi import APIRouter, Depends

from app.log import logger
from app.schemas.base import Success
from app.schemas.kiosk import KioskCreateGuestRequest, KioskGuestResponse
from app.services.kiosk.auth import KioskRequestContext, authorize_kiosk_request
from app.services.nce import NCEClient, NCEGuestCreateRequest, get_nce_client
from app.settings import settings

router = APIRouter(tags=["取号机认证"])


@router.post("/create-guest", summary="创建取号机临时访客账号")
async def create_kiosk_guest(
    _: KioskCreateGuestRequest,
    context: KioskRequestContext = Depends(authorize_kiosk_request),
    nce_client: NCEClient = Depends(get_nce_client),
) -> Success:
    guest = await nce_client.create_guest(
        NCEGuestCreateRequest(
            request_id=context.request_id,
            username_prefix="kiosk",
            valid_duration_minutes=settings.KIOSK_GUEST_VALID_MINUTES,
            max_devices=1,
            description="Kiosk Self-service",
        )
    )
    logger.info(
        "event=kiosk_guest_created kiosk_id={} request_id={} valid_minutes={} max_devices={}",
        context.kiosk_id,
        context.request_id,
        settings.KIOSK_GUEST_VALID_MINUTES,
        guest.max_devices,
    )
    response = KioskGuestResponse(
        username=guest.username,
        password=guest.password,
        validDurationMinutes=settings.KIOSK_GUEST_VALID_MINUTES,
        expireTime=guest.valid_until,
        maxDevices=guest.max_devices,
        ssid=settings.WIFI_SSID,
    )
    return Success(data=response.model_dump(mode="json", by_alias=True))
