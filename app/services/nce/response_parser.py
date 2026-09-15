from collections.abc import Mapping
from datetime import datetime, timezone
from typing import Any

from .client import NCEAuthorizationResult, NCEAuthorizationStatus
from .errors import NCEBusinessError, NCEProtocolError


def require_mapping(value: Any, context: str) -> Mapping[str, Any]:
    if not isinstance(value, Mapping):
        raise NCEProtocolError(f"NCE {context}响应结构无效")
    return value


def require_success_envelope(payload: Any, context: str) -> Mapping[str, Any]:
    envelope = require_mapping(payload, context)
    result_code = str(envelope.get("errcode", ""))
    if result_code != "0":
        raise NCEBusinessError(result_code or "UNKNOWN", f"NCE {context}失败")
    return envelope


def require_string(mapping: Mapping[str, Any], key: str, context: str) -> str:
    value = mapping.get(key)
    if not isinstance(value, str) or not value:
        raise NCEProtocolError(f"NCE {context}响应缺少{key}")
    return value


def parse_nce_datetime(value: Any, context: str) -> datetime:
    if isinstance(value, (int, float)):
        seconds = float(value) / 1000 if value > 10_000_000_000 else float(value)
        return datetime.fromtimestamp(seconds, tz=timezone.utc)
    if isinstance(value, str):
        text = value.strip()
        if text.isdigit():
            return parse_nce_datetime(int(text), context)
        try:
            parsed = datetime.fromisoformat(text.replace("Z", "+00:00"))
        except ValueError:
            try:
                parsed = datetime.strptime(text, "%Y-%m-%d %H:%M:%S")
            except ValueError as exc:
                raise NCEProtocolError(f"NCE {context}时间格式无效") from exc
        return parsed.replace(tzinfo=timezone.utc) if parsed.tzinfo is None else parsed
    raise NCEProtocolError(f"NCE {context}时间格式无效")


def parse_authorization_result(
    payload: Any,
    *,
    status_field: str,
    success_values: set[str],
    pending_values: set[str],
    failure_values: set[str],
) -> NCEAuthorizationResult:
    envelope = require_success_envelope(payload, "HACA授权结果")
    data = envelope.get("data")
    source = data if isinstance(data, Mapping) else envelope
    session_id = source.get("psessionid") or envelope.get("psessionid")
    if not isinstance(session_id, str) or not session_id:
        raise NCEProtocolError("NCE HACA响应缺少psessionid")

    raw_status = source.get(status_field)
    if raw_status is None:
        status = NCEAuthorizationStatus.PENDING
    else:
        normalized = str(raw_status).strip().casefold()
        if normalized in success_values:
            status = NCEAuthorizationStatus.SUCCESS
        elif normalized in failure_values:
            status = NCEAuthorizationStatus.FAILED
        elif normalized in pending_values:
            status = NCEAuthorizationStatus.PENDING
        else:
            status = NCEAuthorizationStatus.PENDING
    result_code = source.get("resultCode", source.get("code", envelope.get("errcode", "0")))
    return NCEAuthorizationResult(session_id=session_id, status=status, result_code=str(result_code))
