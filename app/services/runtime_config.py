from pydantic import BaseModel, ConfigDict

from app.settings.config import Settings


class RuntimeConfigSummary(BaseModel):
    model_config = ConfigDict(frozen=True)

    nce_mode: str
    nce_mock_scenario: str | None
    nce_base_url_configured: bool
    nce_portal_url_configured: bool
    nce_credentials_configured: bool
    nce_site_configured: bool
    redis_configured: bool
    kiosk_hmac_configured: bool
    nce_timeout_ms: int
    auth_transaction_ttl_seconds: int
    kiosk_guest_valid_minutes: int


def build_runtime_config_summary(config: Settings) -> RuntimeConfigSummary:
    """Build a safe operational summary without returning any secret values."""

    return RuntimeConfigSummary(
        nce_mode="mock" if config.NCE_MOCK_ENABLED else "real",
        nce_mock_scenario=config.NCE_MOCK_SCENARIO if config.NCE_MOCK_ENABLED else None,
        nce_base_url_configured=bool(config.NCE_BASE_URL),
        nce_portal_url_configured=bool(config.NCE_PORTAL_AUTH_BASE_URL),
        nce_credentials_configured=bool(config.NCE_USERNAME and config.NCE_PASSWORD),
        nce_site_configured=bool(config.NCE_TENANT_ID and config.NCE_SITE_ID and config.NCE_USER_GROUP_ID),
        redis_configured=bool(config.REDIS_URL),
        kiosk_hmac_configured=bool(config.KIOSK_HMAC_SECRET),
        nce_timeout_ms=config.NCE_TIMEOUT_MS,
        auth_transaction_ttl_seconds=config.AUTH_TRANSACTION_TTL_SECONDS,
        kiosk_guest_valid_minutes=config.KIOSK_GUEST_VALID_MINUTES,
    )
