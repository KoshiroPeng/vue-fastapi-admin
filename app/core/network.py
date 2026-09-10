import ipaddress


def _normalize_ip(value: str) -> str:
    return ipaddress.ip_address(value.strip()).compressed


def resolve_client_ip(peer_ip: str, forwarded_for: str | None, trusted_proxies: list[str]) -> str:
    """Resolve the client IP without trusting spoofable forwarding headers."""

    normalized_peer = _normalize_ip(peer_ip)
    normalized_proxies = {_normalize_ip(value) for value in trusted_proxies}
    if normalized_peer not in normalized_proxies or not forwarded_for:
        return normalized_peer
    if len(forwarded_for) > 512:
        raise ValueError("X-Forwarded-For 过长")
    original_client = forwarded_for.split(",", maxsplit=1)[0]
    return _normalize_ip(original_client)
