from app.core.init_app import make_middlewares
from app.core.middlewares import HttpAuditLogMiddleware


def test_kiosk_credentials_are_excluded_from_body_audit_logging() -> None:
    audit_middleware = next(item for item in make_middlewares() if item.cls is HttpAuditLogMiddleware)

    assert "/api/v1/kiosk/" in audit_middleware.kwargs["exclude_paths"]
