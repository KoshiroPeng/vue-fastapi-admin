import ipaddress


def _normalize_ip(value: str) -> str:
    return ipaddress.ip_address(value.strip()).compressed


def _is_trusted_proxy(peer_ip: str, trusted_proxies: list[str]) -> bool:
    peer = ipaddress.ip_address(peer_ip)
    return any(peer in ipaddress.ip_network(value.strip(), strict=False) for value in trusted_proxies)


def resolve_client_ip(peer_ip: str, forwarded_for: str | None, trusted_proxies: list[str]) -> str:
    """Resolve the client IP without trusting spoofable forwarding headers."""

    normalized_peer = _normalize_ip(peer_ip)
    if not _is_trusted_proxy(normalized_peer, trusted_proxies) or not forwarded_for:
        return normalized_peer
    if len(forwarded_for) > 512:
        raise ValueError("X-Forwarded-For 过长")
    original_client = forwarded_for.split(",", maxsplit=1)[0]
    return _normalize_ip(original_client)
