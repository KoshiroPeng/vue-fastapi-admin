from app.core.network import resolve_client_ip


def test_trusted_proxy_uses_original_forwarded_client_ip() -> None:
    assert (
        resolve_client_ip(
            peer_ip="127.0.0.1",
            forwarded_for="10.20.30.40, 127.0.0.1",
            trusted_proxies=["127.0.0.1"],
        )
        == "10.20.30.40"
    )


def test_untrusted_peer_cannot_spoof_forwarded_client_ip() -> None:
    assert (
        resolve_client_ip(
            peer_ip="192.0.2.10",
            forwarded_for="10.20.30.40",
            trusted_proxies=["127.0.0.1"],
        )
        == "192.0.2.10"
    )
