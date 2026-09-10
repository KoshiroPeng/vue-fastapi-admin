from app.services.kiosk.signing import build_kiosk_signature, verify_kiosk_signature


def test_kiosk_signature_binds_method_path_headers_and_body() -> None:
    body = b'{"idType":"ID_CARD","idDigest":"aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa"}'
    signature = build_kiosk_signature(
        secret="test-kiosk-secret",
        method="POST",
        path="/api/v1/kiosk/create-guest",
        kiosk_id="KIOSK-T3-001",
        timestamp="1789027200",
        nonce="nonce-001",
        idempotency_key="request-001",
        body=body,
    )

    assert signature == "f71670fd3f13031403e985ebd7deb4c9ffe38be184a0474181046c63c338888e"
    assert verify_kiosk_signature(
        signature=signature,
        secret="test-kiosk-secret",
        method="POST",
        path="/api/v1/kiosk/create-guest",
        kiosk_id="KIOSK-T3-001",
        timestamp="1789027200",
        nonce="nonce-001",
        idempotency_key="request-001",
        body=body,
    )
    assert not verify_kiosk_signature(
        signature=signature,
        secret="test-kiosk-secret",
        method="POST",
        path="/api/v1/kiosk/create-guest",
        kiosk_id="KIOSK-T3-001",
        timestamp="1789027200",
        nonce="nonce-001",
        idempotency_key="request-001",
        body=body + b" ",
    )
