import hmac
import time

from fastapi import APIRouter, Depends, Header, HTTPException, Request

from app.core.masking import hash_ip, hash_mac
from app.core.request_context import get_request_id
from app.schemas.base import Success
from app.schemas.portal import BoardingPassPortalRequest, WeChatCallbackRequest, WeChatStartRequest
from app.services.boarding_pass import BoardingPassAuthRequest, BoardingPassAuthenticationService, BoardingPassRejected
from app.services.passport import PassportAuthenticationService, PassportImage, PassportOCRRejected
from app.services.portal_factory import get_boarding_pass_service, get_passport_service, get_wechat_service
from app.services.risk_control import (
    RedisReplayProtector,
    RedisSlidingWindowRateLimiter,
    get_rate_limiter,
    get_replay_protector,
    validate_request_timestamp,
)
from app.services.wechat import WeChatAuthService, WeChatCallbackRejected, build_wechat_signature
from app.settings import settings

router = APIRouter(tags=["旅客认证"])


async def _limit_client(
    client_ip: str,
    client_mac: str,
    limiter: RedisSlidingWindowRateLimiter,
    scope: str,
) -> None:
    secret = settings.PII_HASH_SECRET
    if not secret:
        raise HTTPException(status_code=503, detail="PII_HASH_SECRET 尚未配置")
    await limiter.check(
        f"{scope}:ip",
        hash_ip(client_ip, secret),
        limit=settings.RATE_LIMIT_PER_IP,
        window_seconds=settings.RATE_LIMIT_WINDOW_SECONDS,
    )
    await limiter.check(
        f"{scope}:mac",
        hash_mac(client_mac, secret),
        limit=settings.RATE_LIMIT_PER_MAC,
        window_seconds=settings.RATE_LIMIT_WINDOW_SECONDS,
    )


@router.post("/boarding-pass/verify", summary="登机牌三要素验证并创建临时访客")
async def verify_boarding_pass(
    payload: BoardingPassPortalRequest,
    service: BoardingPassAuthenticationService = Depends(get_boarding_pass_service),
    limiter: RedisSlidingWindowRateLimiter = Depends(get_rate_limiter),
) -> Success:
    await _limit_client(payload.client_ip, payload.client_mac, limiter, "boarding-pass")
    try:
        result = await service.authenticate(
            BoardingPassAuthRequest(
                flight_date=payload.flight_date,
                flight_no=payload.flight_no,
                seat_no=payload.seat_no,
                document_last4=payload.document_last4,
                client_ip=payload.client_ip,
                client_mac=payload.client_mac,
                ssid=payload.ssid,
            ),
            trace_id=get_request_id() or "-",
        )
    except BoardingPassRejected as exc:
        raise HTTPException(status_code=400, detail="登机信息验证未通过，请检查后重试或选择其他认证方式") from exc
    return Success(
        data={
            "verified": True,
            "authTxId": result.auth_tx_id,
            "tempUsername": result.username,
            "tempPassword": result.password.get_secret_value(),
            "validUntil": result.valid_until.isoformat(),
        }
    )


@router.post(
    "/passport/verify",
    summary="护照图像流识别并创建临时访客",
    openapi_extra={
        "requestBody": {
            "required": True,
            "content": {
                "image/jpeg": {"schema": {"type": "string", "format": "binary"}},
                "image/png": {"schema": {"type": "string", "format": "binary"}},
            },
        }
    },
)
async def verify_passport(
    request: Request,
    client_ip: str = Header(alias="X-Client-IP", max_length=64),
    client_mac: str = Header(alias="X-Client-MAC", max_length=32),
    ssid: str | None = Header(default=None, alias="X-SSID", max_length=64),
    service: PassportAuthenticationService = Depends(get_passport_service),
    limiter: RedisSlidingWindowRateLimiter = Depends(get_rate_limiter),
) -> Success:
    await _limit_client(client_ip, client_mac, limiter, "passport")
    content_type = request.headers.get("Content-Type", "").split(";", maxsplit=1)[0].lower()
    if content_type not in {"image/jpeg", "image/png"}:
        raise HTTPException(status_code=400, detail="仅支持 JPG 或 PNG 护照图像")
    content_length = request.headers.get("Content-Length")
    if content_length:
        try:
            declared_size = int(content_length)
        except ValueError as exc:
            raise HTTPException(status_code=400, detail="Content-Length 无效") from exc
        if declared_size < 0 or declared_size > settings.PASSPORT_MAX_IMAGE_BYTES:
            raise HTTPException(status_code=413, detail="护照图像超过大小限制")
    image_buffer = bytearray()
    async for chunk in request.stream():
        image_buffer.extend(chunk)
        if len(image_buffer) > settings.PASSPORT_MAX_IMAGE_BYTES:
            image_buffer.clear()
            raise HTTPException(status_code=413, detail="护照图像超过大小限制")
    try:
        result = await service.authenticate(
            image=PassportImage(content=bytes(image_buffer), content_type=content_type),
            client_ip=client_ip,
            client_mac=client_mac,
            ssid=ssid,
            trace_id=get_request_id() or "-",
        )
    except (ValueError, PassportOCRRejected) as exc:
        raise HTTPException(status_code=400, detail="护照识别未通过，请重新拍摄") from exc
    finally:
        image_buffer.clear()
    return Success(
        data={
            "verified": True,
            "authTxId": result.auth_tx_id,
            "passportNoMasked": result.passport_number_masked,
            "tempUsername": result.username,
            "tempPassword": result.password.get_secret_value(),
            "validUntil": result.valid_until.isoformat(),
        }
    )


@router.post("/wechat/auth/start", summary="创建微信认证短时事务")
async def start_wechat_auth(
    payload: WeChatStartRequest,
    service: WeChatAuthService = Depends(get_wechat_service),
    limiter: RedisSlidingWindowRateLimiter = Depends(get_rate_limiter),
) -> Success:
    await _limit_client(payload.client_ip, payload.client_mac, limiter, "wechat")
    transaction = await service.start(
        client_ip=payload.client_ip,
        client_mac=payload.client_mac,
        ssid=payload.ssid,
        trace_id=get_request_id() or "-",
    )
    return Success(
        data={
            "authTxId": transaction.auth_tx_id,
            "status": transaction.status.value,
            "expireAt": transaction.expire_at.isoformat(),
        }
    )


@router.post("/wechat/auth/callback", summary="接收微信认证状态回写")
async def callback_wechat_auth(
    request: Request,
    payload: WeChatCallbackRequest,
    signature: str = Header(alias="X-Wx-Signature", min_length=64, max_length=64),
    timestamp: str = Header(alias="X-Wx-Timestamp", min_length=1, max_length=20),
    nonce: str = Header(alias="X-Wx-Nonce", min_length=8, max_length=128),
    service: WeChatAuthService = Depends(get_wechat_service),
    replay: RedisReplayProtector = Depends(get_replay_protector),
) -> Success:
    try:
        numeric_timestamp = int(timestamp)
    except ValueError as exc:
        raise HTTPException(status_code=401, detail="微信回写时间戳无效") from exc
    validate_request_timestamp(numeric_timestamp, int(time.time()), settings.WECHAT_CALLBACK_CLOCK_SKEW_SECONDS)
    raw_body = await request.body()
    callback_secret = settings.WECHAT_CALLBACK_SECRET or ""
    expected_signature = build_wechat_signature(callback_secret, timestamp, nonce, raw_body)
    if not hmac.compare_digest(signature.lower(), expected_signature):
        raise HTTPException(status_code=401, detail="微信状态回写签名无效")
    await replay.claim("wechat-callback", nonce, settings.NONCE_TTL_SECONDS)
    try:
        transaction = await service.apply_callback(
            auth_tx_id=payload.auth_tx_id,
            result=payload.result,
            nce_success=payload.nce_success,
            timestamp=timestamp,
            nonce=nonce,
            body=raw_body,
            signature=signature,
        )
    except WeChatCallbackRejected as exc:
        raise HTTPException(status_code=401, detail="微信状态回写签名无效") from exc
    return Success(data={"authTxId": transaction.auth_tx_id, "status": transaction.status.value})


@router.post("/wechat/auth/mock-complete", summary="开发环境模拟微信 NCE 放行")
async def mock_complete_wechat_auth(
    auth_tx_id: str,
    service: WeChatAuthService = Depends(get_wechat_service),
) -> Success:
    if not (settings.DEBUG and settings.NCE_MOCK_ENABLED):
        raise HTTPException(status_code=404, detail="接口不存在")
    transaction = await service.mock_complete(auth_tx_id)
    return Success(data={"authTxId": transaction.auth_tx_id, "status": transaction.status.value})


@router.get("/wechat/auth/status", summary="查询微信认证短时事务状态")
async def get_wechat_auth_status(
    auth_tx_id: str,
    service: WeChatAuthService = Depends(get_wechat_service),
) -> Success:
    transaction = await service.status(auth_tx_id)
    if transaction is None:
        raise HTTPException(status_code=404, detail="认证事务不存在或已过期")
    return Success(
        data={
            "authTxId": transaction.auth_tx_id,
            "status": transaction.status.value,
            "expireAt": transaction.expire_at.isoformat(),
        }
    )
