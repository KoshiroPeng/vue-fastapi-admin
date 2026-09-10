from pydantic import BaseModel, ConfigDict

from app.settings.config import Settings


class RuntimeConfigSummary(BaseModel):
    model_config = ConfigDict(frozen=True)

    app_env: str
    wifi_ssid: str
    nce_mode: str
    nce_mock_scenario: str | None
    nce_site_id: str | None
    nce_guest_user_group_id: str | None
    nce_base_url_configured: bool
    nce_portal_url_configured: bool
    nce_credentials_configured: bool
    nce_site_configured: bool
    redis_configured: bool
    pii_hash_secret_configured: bool
    kiosk_hmac_configured: bool
    nce_timeout_ms: int
    auth_transaction_ttl_seconds: int
    nonce_ttl_seconds: int
    idempotency_ttl_seconds: int
    kiosk_guest_valid_minutes: int
    kiosk_max_body_bytes: int
    rate_limit_per_ip: int
    rate_limit_per_mac: int
    auth_methods: dict[str, bool]


def build_runtime_config_summary(config: Settings) -> RuntimeConfigSummary:
    """Build a safe operational summary without returning any secret values."""

    return RuntimeConfigSummary(
        app_env=config.APP_ENV,
        wifi_ssid=config.WIFI_SSID,
        nce_mode="mock" if config.NCE_MOCK_ENABLED else "real",
        nce_mock_scenario=config.NCE_MOCK_SCENARIO if config.NCE_MOCK_ENABLED else None,
        nce_site_id=config.NCE_SITE_ID,
        nce_guest_user_group_id=config.NCE_GUEST_USER_GROUP_ID,
        nce_base_url_configured=bool(config.NCE_BASE_URL),
        nce_portal_url_configured=bool(config.NCE_PORTAL_AUTH_BASE_URL),
        nce_credentials_configured=bool(config.NCE_USERNAME and config.NCE_PASSWORD),
        nce_site_configured=bool(config.NCE_TENANT_ID and config.NCE_SITE_ID and config.NCE_GUEST_USER_GROUP_ID),
        redis_configured=bool(config.REDIS_URL),
        pii_hash_secret_configured=bool(config.PII_HASH_SECRET),
        kiosk_hmac_configured=bool(config.KIOSK_HMAC_SECRET),
        nce_timeout_ms=config.NCE_TIMEOUT_MS,
        auth_transaction_ttl_seconds=config.AUTH_TRANSACTION_TTL_SECONDS,
        nonce_ttl_seconds=config.NONCE_TTL_SECONDS,
        idempotency_ttl_seconds=config.IDEMPOTENCY_TTL_SECONDS,
        kiosk_guest_valid_minutes=config.KIOSK_GUEST_VALID_MINUTES,
        kiosk_max_body_bytes=config.KIOSK_MAX_BODY_BYTES,
        rate_limit_per_ip=config.RATE_LIMIT_PER_IP,
        rate_limit_per_mac=config.RATE_LIMIT_PER_MAC,
        auth_methods={
            "sms": config.AUTH_SMS_ENABLED,
            "wechat": config.AUTH_WECHAT_ENABLED,
            "boarding_pass": config.AUTH_BOARDING_PASS_ENABLED,
            "passport": config.AUTH_PASSPORT_ENABLED,
            "kiosk": config.AUTH_KIOSK_ENABLED,
        },
    )
