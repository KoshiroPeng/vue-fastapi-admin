import pytest
from pydantic import ValidationError

from app.services.runtime_config import build_runtime_config_summary
from app.settings.config import Settings


def test_runtime_config_summary_never_exposes_secrets() -> None:
    config = Settings(
        _env_file=None,
        NCE_MOCK_ENABLED=True,
        NCE_USERNAME="mock-operator",
        NCE_PASSWORD="nce-secret-value",
        NCE_SITE_ID="site-visible-for-operations",
        NCE_GUEST_USER_GROUP_ID="guest-group-visible-for-operations",
        KIOSK_HMAC_SECRET="kiosk-secret-value",
        PII_HASH_SECRET="pii-hash-secret-value",
        AUTH_PASSPORT_ENABLED=False,
        MINI_PROGRAM_GUEST_SERVICE_URL="https://nce.example/guest",
        MINI_PROGRAM_PORTAL_AUTH_URL="https://nce.example/auth",
    )

    summary = build_runtime_config_summary(config)
    serialized = summary.model_dump_json()

    assert summary.nce_mode == "mock"
    assert summary.nce_credentials_configured is True
    assert summary.kiosk_hmac_configured is True
    assert summary.pii_hash_secret_configured is True
    assert summary.nce_site_id == "site-visible-for-operations"
    assert summary.nce_guest_user_group_id == "guest-group-visible-for-operations"
    assert summary.auth_methods["kiosk"] is True
    assert summary.auth_methods["passport"] is False
    assert summary.nce_kick_enabled is False
    assert summary.nce_max_connections == 100
    assert summary.nce_max_keepalive_connections == 50
    assert summary.nce_tls_verify is True
    assert summary.nce_ca_file_configured is False
    assert summary.nce_haca_policy_configured is False
    assert summary.nce_haca_poll_attempts == 10
    assert summary.mini_program_guest_service_configured is True
    assert summary.mini_program_portal_auth_configured is True
    assert summary.mini_program_tls_verify is True
    assert "nce-secret-value" not in serialized
    assert "nce-secret-value" not in repr(config)
    assert "kiosk-secret-value" not in serialized
    assert "pii-hash-secret-value" not in serialized
    assert "mock-operator" not in serialized


def test_mysql_config_uses_pool_and_never_exposes_secret() -> None:
    config = Settings(
        _env_file=None,
        MYSQL_HOST="mysql.internal",
        MYSQL_PORT=6612,
        MYSQL_USER="wifi_app",
        MYSQL_PASSWORD="database-secret",
        MYSQL_DATABASE="wifi_admin",
        MYSQL_POOL_MIN_SIZE=3,
        MYSQL_POOL_MAX_SIZE=12,
    )

    credentials = config.TORTOISE_ORM["connections"]["default"]["credentials"]

    assert credentials["host"] == "mysql.internal"
    assert credentials["port"] == 6612
    assert credentials["user"] == "wifi_app"
    assert credentials["password"] == "database-secret"
    assert credentials["database"] == "wifi_admin"
    assert credentials["minsize"] == 3
    assert credentials["maxsize"] == 12
    assert "database-secret" not in repr(config)


def test_production_rejects_development_secret_and_wildcard_cors() -> None:
    with pytest.raises(ValidationError, match="SECRET_KEY"):
        Settings(_env_file=None, APP_ENV="production")

    with pytest.raises(ValidationError, match="CORS"):
        Settings(
            _env_file=None,
            APP_ENV="production",
            DEBUG=False,
            NCE_MOCK_ENABLED=False,
            BOARDING_PASS_MOCK_ENABLED=False,
            OCR_MOCK_ENABLED=False,
            SECRET_KEY="a-production-secret-that-is-at-least-32-characters",
            CORS_ORIGINS=["*"],
        )

    with pytest.raises(ValidationError, match="Mock"):
        Settings(
            _env_file=None,
            APP_ENV="production",
            DEBUG=False,
            SECRET_KEY="a-production-secret-that-is-at-least-32-characters",
        )
