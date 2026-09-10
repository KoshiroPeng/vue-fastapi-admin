import hashlib
import hmac


def _canonical_request(
    method: str,
    path: str,
    kiosk_id: str,
    timestamp: str,
    nonce: str,
    idempotency_key: str,
    body: bytes,
) -> bytes:
    body_digest = hashlib.sha256(body).hexdigest()
    fields = [method.upper(), path, kiosk_id, timestamp, nonce, idempotency_key, body_digest]
    return "\n".join(fields).encode("utf-8")


def build_kiosk_signature(
    *,
    secret: str,
    method: str,
    path: str,
    kiosk_id: str,
    timestamp: str,
    nonce: str,
    idempotency_key: str,
    body: bytes,
) -> str:
    if not secret:
        raise ValueError("取号机 HMAC 密钥不能为空")
    canonical = _canonical_request(method, path, kiosk_id, timestamp, nonce, idempotency_key, body)
    return hmac.new(secret.encode("utf-8"), canonical, hashlib.sha256).hexdigest()


def verify_kiosk_signature(*, signature: str, **request_fields: str | bytes) -> bool:
    try:
        expected = build_kiosk_signature(**request_fields)
    except (TypeError, ValueError):
        return False
    return hmac.compare_digest(signature.lower(), expected)
