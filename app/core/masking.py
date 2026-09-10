import hashlib
import hmac
import ipaddress
import re

_MAC_HEX_PATTERN = re.compile(r"^[0-9A-Fa-f]{12}$")


def _require_secret(secret: str) -> bytes:
    if not secret:
        raise ValueError("哈希密钥不能为空")
    return secret.encode("utf-8")


def _fingerprint(namespace: str, normalized_value: str, secret: str) -> str:
    payload = f"{namespace}:{normalized_value}".encode("utf-8")
    return hmac.new(_require_secret(secret), payload, hashlib.sha256).hexdigest()


def normalize_mac(value: str) -> str:
    compact = value.replace(":", "").replace("-", "").replace(".", "")
    if not _MAC_HEX_PATTERN.fullmatch(compact):
        raise ValueError("MAC 地址格式无效")
    return compact.upper()


def hash_mac(value: str, secret: str) -> str:
    return _fingerprint("mac", normalize_mac(value), secret)


def hash_ip(value: str, secret: str) -> str:
    normalized = ipaddress.ip_address(value).compressed
    return _fingerprint("ip", normalized, secret)


def mask_account(value: str) -> str:
    sms_match = re.fullmatch(r"(sms_)(1\d{2})\d{4}(\d{4})", value, flags=re.IGNORECASE)
    if sms_match:
        return f"{sms_match.group(1)}{sms_match.group(2)}****{sms_match.group(3)}"
    if len(value) <= 4:
        return "*" * len(value)
    return f"{value[:3]}****{value[-4:]}"


def mask_mac(value: str) -> str:
    normalized = normalize_mac(value)
    octets = [normalized[index : index + 2] for index in range(0, 12, 2)]
    return f"{octets[0]}:**:**:**:**:{octets[-1]}"


def mask_ip(value: str) -> str:
    address = ipaddress.ip_address(value)
    if address.version == 4:
        octets = address.compressed.split(".")
        return f"{octets[0]}.***.***.{octets[-1]}"
    parts = address.exploded.split(":")
    return f"{parts[0]}:****:****:****:****:****:****:{parts[-1]}"
