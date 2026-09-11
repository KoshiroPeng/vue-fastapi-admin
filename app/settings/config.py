import os
import typing

from pydantic import SecretStr, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    DEVELOPMENT_SECRET_KEY: typing.ClassVar[str] = "development-only-secret-key-change-before-production"

    VERSION: str = "0.1.0"
    APP_TITLE: str = "深圳机场WiFi管理台"
    PROJECT_NAME: str = "深圳机场WiFi管理台"
    APP_DESCRIPTION: str = "Description"

    CORS_ORIGINS: list[str] = ["http://localhost:3100"]
    CORS_ALLOW_CREDENTIALS: bool = True
    CORS_ALLOW_METHODS: typing.List = ["*"]
    CORS_ALLOW_HEADERS: typing.List = ["*"]

    DEBUG: bool = True
    APP_ENV: typing.Literal["development", "test", "production"] = "development"

    # WiFi authentication gateway. Mock mode is the safe default until a real
    # NCE test environment and its credentials have been approved.
    NCE_MOCK_ENABLED: bool = True
    NCE_MOCK_SCENARIO: typing.Literal[
        "healthy",
        "auth_failure",
        "business_failure",
        "timeout",
        "unavailable",
    ] = "healthy"
    NCE_BASE_URL: str | None = None
    NCE_PORTAL_AUTH_BASE_URL: str | None = None
    NCE_USERNAME: str | None = None
    NCE_PASSWORD: str | None = None
    NCE_TENANT_ID: str | None = None
    NCE_SITE_ID: str | None = None
    NCE_GUEST_USER_GROUP_ID: str | None = None
    NCE_TIMEOUT_MS: int = 2500
    NCE_KICK_ENABLED: bool = False

    AUTH_SMS_ENABLED: bool = True
    AUTH_WECHAT_ENABLED: bool = True
    AUTH_BOARDING_PASS_ENABLED: bool = True
    AUTH_PASSPORT_ENABLED: bool = True
    AUTH_KIOSK_ENABLED: bool = True
    BOARDING_PASS_MOCK_ENABLED: bool = True
    OCR_MOCK_ENABLED: bool = True
    BOARDING_PASS_GUEST_VALID_MINUTES: int = 480
    PASSPORT_GUEST_VALID_MINUTES: int = 480
    PASSPORT_MAX_IMAGE_BYTES: int = 4 * 1024 * 1024
    WECHAT_CALLBACK_SECRET: str | None = None
    WECHAT_CALLBACK_CLOCK_SKEW_SECONDS: int = 300

    REDIS_URL: str = "redis://127.0.0.1:6379/0"
    MYSQL_HOST: str = "127.0.0.1"
    MYSQL_PORT: int = 3306
    MYSQL_USER: str = "vue_fastapi_admin"
    MYSQL_PASSWORD: SecretStr | None = None
    MYSQL_DATABASE: str = "vue_fastapi_admin"
    MYSQL_POOL_MIN_SIZE: int = 2
    MYSQL_POOL_MAX_SIZE: int = 10
    MYSQL_CONNECT_TIMEOUT_SECONDS: int = 10
    PII_HASH_SECRET: str | None = None
    AUTH_TRANSACTION_TTL_SECONDS: int = 300
    NONCE_TTL_SECONDS: int = 300
    IDEMPOTENCY_TTL_SECONDS: int = 300
    RATE_LIMIT_WINDOW_SECONDS: int = 60
    RATE_LIMIT_PER_IP: int = 30
    RATE_LIMIT_PER_MAC: int = 5
    DASHBOARD_ONLINE_CACHE_TTL_SECONDS: int = 5
    DASHBOARD_RADIUS_CACHE_TTL_SECONDS: int = 10
    DASHBOARD_STATISTICS_CACHE_TTL_SECONDS: int = 30
    EXTERNAL_CALL_LOG_RETENTION_DAYS: int = 30

    KIOSK_HMAC_SECRET: str | None = None
    TRUSTED_PROXY_IPS: list[str] = ["127.0.0.1", "::1"]
    KIOSK_ALLOWED_IPS: list[str] = ["127.0.0.1", "::1"]
    KIOSK_CLOCK_SKEW_SECONDS: int = 300
    KIOSK_GUEST_VALID_MINUTES: int = 1440
    KIOSK_MAX_BODY_BYTES: int = 8192
    WIFI_SSID: str = "Airport-Free-WiFi"

    PROJECT_ROOT: str = os.path.abspath(os.path.join(os.path.dirname(__file__), os.pardir))
    BASE_DIR: str = os.path.abspath(os.path.join(PROJECT_ROOT, os.pardir))
    LOGS_ROOT: str = os.path.join(BASE_DIR, "logs")
    SECRET_KEY: str = DEVELOPMENT_SECRET_KEY
    JWT_ALGORITHM: str = "HS256"
    JWT_ACCESS_TOKEN_EXPIRE_MINUTES: int = 60 * 24 * 7  # 7 day
    DATETIME_FORMAT: str = "%Y-%m-%d %H:%M:%S"

    @property
    def TORTOISE_ORM(self) -> dict:
        return {
            "connections": {
                "default": {
                    "engine": "tortoise.backends.mysql",
                    "credentials": {
                        "host": self.MYSQL_HOST,
                        "port": self.MYSQL_PORT,
                        "user": self.MYSQL_USER,
                        "password": self.MYSQL_PASSWORD.get_secret_value() if self.MYSQL_PASSWORD else "",
                        "database": self.MYSQL_DATABASE,
                        "charset": "utf8mb4",
                        "storage_engine": "InnoDB",
                        "minsize": self.MYSQL_POOL_MIN_SIZE,
                        "maxsize": self.MYSQL_POOL_MAX_SIZE,
                        "connect_timeout": self.MYSQL_CONNECT_TIMEOUT_SECONDS,
                    },
                }
            },
            "apps": {
                "models": {
                        "models": ["app.models"],
                    "default_connection": "default",
                }
            },
            "use_tz": False,
            "timezone": "Asia/Shanghai",
        }

    @model_validator(mode="after")
    def validate_production_security(self) -> "Settings":
        if self.APP_ENV != "production":
            return self
        if self.SECRET_KEY == self.DEVELOPMENT_SECRET_KEY or len(self.SECRET_KEY) < 32:
            raise ValueError("生产环境必须通过 SECRET_KEY 注入至少 32 字符的独立密钥")
        if self.DEBUG:
            raise ValueError("生产环境必须设置 DEBUG=false")
        if self.NCE_MOCK_ENABLED or self.BOARDING_PASS_MOCK_ENABLED or self.OCR_MOCK_ENABLED:
            raise ValueError("生产环境禁止启用 Mock 外部服务")
        if "*" in self.CORS_ORIGINS:
            raise ValueError("生产环境 CORS_ORIGINS 禁止使用通配符")
        if not self.MYSQL_PASSWORD:
            raise ValueError("生产环境必须配置 MYSQL_PASSWORD")
        if self.MYSQL_POOL_MIN_SIZE <= 0 or self.MYSQL_POOL_MAX_SIZE < self.MYSQL_POOL_MIN_SIZE:
            raise ValueError("MySQL 连接池参数无效")
        return self


settings = Settings()
