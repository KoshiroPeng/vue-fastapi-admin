from app.services.runtime_config import build_runtime_config_summary
from app.settings.config import Settings


def test_runtime_config_summary_never_exposes_secrets() -> None:
    config = Settings(
        _env_file=None,
        NCE_MOCK_ENABLED=True,
        NCE_USERNAME="mock-operator",
        NCE_PASSWORD="nce-secret-value",
        KIOSK_HMAC_SECRET="kiosk-secret-value",
        PII_HASH_SECRET="pii-hash-secret-value",
    )

    summary = build_runtime_config_summary(config)
    serialized = summary.model_dump_json()

    assert summary.nce_mode == "mock"
    assert summary.nce_credentials_configured is True
    assert summary.kiosk_hmac_configured is True
    assert summary.pii_hash_secret_configured is True
    assert "nce-secret-value" not in serialized
    assert "kiosk-secret-value" not in serialized
    assert "pii-hash-secret-value" not in serialized
