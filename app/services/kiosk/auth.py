import hashlib
import time
from dataclasses import dataclass

from fastapi import Depends, Header, HTTPException, Request

from app.core.masking import hash_ip
from app.core.network import resolve_client_ip
from app.services.risk_control import (
    RedisIdempotencyGuard,
    RedisReplayProtector,
    RedisSlidingWindowRateLimiter,
    get_idempotency_guard,
    get_rate_limiter,
    get_replay_protector,
    validate_request_timestamp,
)
from app.settings import settings

from .signing import verify_kiosk_signature


@dataclass(frozen=True)
class KioskRequestContext:
    kiosk_id: str
    request_id: str
    source_ip_hash: str


async def authorize_kiosk_request(
    request: Request,
    kiosk_id: str = Header(
        alias="X-Kiosk-Id",
        pattern=r"^[A-Za-z0-9][A-Za-z0-9._-]{0,63}$",
    ),
    timestamp: str = Header(alias="X-Timestamp", min_length=1, max_length=20),
    nonce: str = Header(alias="X-Nonce", min_length=8, max_length=128),
    signature: str = Header(alias="X-Signature", min_length=64, max_length=64),
    idempotency_key: str = Header(alias="Idempotency-Key", min_length=8, max_length=128),
    replay_protector: RedisReplayProtector = Depends(get_replay_protector),
    rate_limiter: RedisSlidingWindowRateLimiter = Depends(get_rate_limiter),
    idempotency_guard: RedisIdempotencyGuard = Depends(get_idempotency_guard),
) -> KioskRequestContext:
    if not settings.KIOSK_HMAC_SECRET or not settings.PII_HASH_SECRET:
        raise HTTPException(status_code=503, detail="取号机认证服务尚未完成安全配置")
    content_length = request.headers.get("Content-Length")
    if content_length is not None:
        try:
            body_size = int(content_length)
        except ValueError as exc:
            raise HTTPException(status_code=400, detail="Content-Length 无效") from exc
        if body_size < 0 or body_size > settings.KIOSK_MAX_BODY_BYTES:
            raise HTTPException(status_code=413, detail="取号机请求体过大")
    peer_ip = request.client.host if request.client else ""
    try:
        source_ip = resolve_client_ip(
            peer_ip=peer_ip,
            forwarded_for=request.headers.get("X-Forwarded-For"),
            trusted_proxies=settings.TRUSTED_PROXY_IPS,
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail="取号机来源地址格式无效") from exc
    if source_ip not in settings.KIOSK_ALLOWED_IPS:
        raise HTTPException(status_code=403, detail="取号机来源地址不在白名单中")
    try:
        numeric_timestamp = int(timestamp)
    except ValueError as exc:
        raise HTTPException(status_code=401, detail="取号机请求时间戳无效") from exc

    body = await request.body()
    if not verify_kiosk_signature(
        signature=signature,
        secret=settings.KIOSK_HMAC_SECRET,
        method=request.method,
        path=request.url.path,
        kiosk_id=kiosk_id,
        timestamp=timestamp,
        nonce=nonce,
        idempotency_key=idempotency_key,
        body=body,
    ):
        raise HTTPException(status_code=401, detail="取号机请求签名无效")

    validate_request_timestamp(
        timestamp=numeric_timestamp,
        now=int(time.time()),
        max_skew_seconds=settings.KIOSK_CLOCK_SKEW_SECONDS,
    )
    source_ip_hash = hash_ip(source_ip, settings.PII_HASH_SECRET)
    await rate_limiter.check(
        "kiosk:ip",
        source_ip_hash,
        limit=settings.RATE_LIMIT_PER_IP,
        window_seconds=settings.RATE_LIMIT_WINDOW_SECONDS,
    )
    await replay_protector.claim("kiosk", nonce, ttl_seconds=settings.NONCE_TTL_SECONDS)
    await idempotency_guard.claim("kiosk", idempotency_key, ttl_seconds=settings.IDEMPOTENCY_TTL_SECONDS)
    request_id = hashlib.sha256(idempotency_key.encode("utf-8")).hexdigest()[:16]
    return KioskRequestContext(kiosk_id=kiosk_id, request_id=request_id, source_ip_hash=source_ip_hash)
