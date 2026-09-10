from app.core.init_app import make_middlewares
from app.core.middlewares import HttpAuditLogMiddleware, sanitize_for_audit


def test_kiosk_credentials_are_excluded_from_body_audit_logging() -> None:
    audit_middleware = next(item for item in make_middlewares() if item.cls is HttpAuditLogMiddleware)

    assert "/api/v1/kiosk/" in audit_middleware.kwargs["exclude_paths"]
    assert "/api/v1/portal/" in audit_middleware.kwargs["exclude_paths"]


def test_audit_sanitizer_redacts_nested_credentials_and_pii() -> None:
    sanitized = sanitize_for_audit(
        {
            "username": "operator",
            "password": "plain-password",
            "data": {
                "temporary_password": "one-time-password",
                "idDigest": "document-digest",
                "result_code": "0000",
            },
            "items": [{"accessToken": "token-value"}],
        }
    )

    assert sanitized["username"] == "***REDACTED***"
    assert sanitized["password"] == "***REDACTED***"
    assert sanitized["data"]["temporary_password"] == "***REDACTED***"
    assert sanitized["data"]["idDigest"] == "***REDACTED***"
    assert sanitized["data"]["result_code"] == "0000"
    assert sanitized["items"][0]["accessToken"] == "***REDACTED***"
