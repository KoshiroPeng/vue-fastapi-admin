import os
import typing

from pydantic import model_validator
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

    REDIS_URL: str = "redis://127.0.0.1:6379/0"
    PII_HASH_SECRET: str | None = None
    AUTH_TRANSACTION_TTL_SECONDS: int = 300
    NONCE_TTL_SECONDS: int = 300
    IDEMPOTENCY_TTL_SECONDS: int = 300
    RATE_LIMIT_WINDOW_SECONDS: int = 60
    RATE_LIMIT_PER_IP: int = 30
    RATE_LIMIT_PER_MAC: int = 5

    KIOSK_HMAC_SECRET: str | None = None
    TRUSTED_PROXY_IPS: list[str] = ["127.0.0.1", "::1"]
    KIOSK_ALLOWED_IPS: list[str] = ["127.0.0.1", "::1"]
    KIOSK_CLOCK_SKEW_SECONDS: int = 300
    KIOSK_GUEST_VALID_MINUTES: int = 1440
    KIOSK_MAX_BODY_BYTES: int = 8192
    WIFI_SSID: str = "Airport-Free-WiFi"

    PROJECT_ROOT: str = os.path.abspath(os.path.join(os.path.dirname(__file__), os.pardir))
    BASE_DIR: str = os.path.abspath(os.path.join(PROJECT_ROOT, os.pardir))
    LOGS_ROOT: str = os.path.join(BASE_DIR, "app/logs")
    SECRET_KEY: str = DEVELOPMENT_SECRET_KEY
    BOOTSTRAP_ADMIN_ENABLED: bool = False
    BOOTSTRAP_ADMIN_USERNAME: str = "admin"
    BOOTSTRAP_ADMIN_EMAIL: str = "admin@admin.com"
    BOOTSTRAP_ADMIN_PASSWORD: str | None = None
    JWT_ALGORITHM: str = "HS256"
    JWT_ACCESS_TOKEN_EXPIRE_MINUTES: int = 60 * 24 * 7  # 7 day
    TORTOISE_ORM: dict = {
        "connections": {
            # SQLite configuration
            "sqlite": {
                "engine": "tortoise.backends.sqlite",
                "credentials": {"file_path": f"{BASE_DIR}/db.sqlite3"},  # Path to SQLite database file
            },
            # MySQL/MariaDB configuration
            # Install with: tortoise-orm[asyncmy]
            # "mysql": {
            #     "engine": "tortoise.backends.mysql",
            #     "credentials": {
            #         "host": "localhost",  # Database host address
            #         "port": 3306,  # Database port
            #         "user": "yourusername",  # Database username
            #         "password": "yourpassword",  # Database password
            #         "database": "yourdatabase",  # Database name
            #     },
            # },
            # PostgreSQL configuration
            # Install with: tortoise-orm[asyncpg]
            # "postgres": {
            #     "engine": "tortoise.backends.asyncpg",
            #     "credentials": {
            #         "host": "localhost",  # Database host address
            #         "port": 5432,  # Database port
            #         "user": "yourusername",  # Database username
            #         "password": "yourpassword",  # Database password
            #         "database": "yourdatabase",  # Database name
            #     },
            # },
            # MSSQL/Oracle configuration
            # Install with: tortoise-orm[asyncodbc]
            # "oracle": {
            #     "engine": "tortoise.backends.asyncodbc",
            #     "credentials": {
            #         "host": "localhost",  # Database host address
            #         "port": 1433,  # Database port
            #         "user": "yourusername",  # Database username
            #         "password": "yourpassword",  # Database password
            #         "database": "yourdatabase",  # Database name
            #     },
            # },
            # SQLServer configuration
            # Install with: tortoise-orm[asyncodbc]
            # "sqlserver": {
            #     "engine": "tortoise.backends.asyncodbc",
            #     "credentials": {
            #         "host": "localhost",  # Database host address
            #         "port": 1433,  # Database port
            #         "user": "yourusername",  # Database username
            #         "password": "yourpassword",  # Database password
            #         "database": "yourdatabase",  # Database name
            #     },
            # },
        },
        "apps": {
            "models": {
                "models": ["app.models", "aerich.models"],
                "default_connection": "sqlite",
            },
        },
        "use_tz": False,  # Whether to use timezone-aware datetimes
        "timezone": "Asia/Shanghai",  # Timezone setting
    }
    DATETIME_FORMAT: str = "%Y-%m-%d %H:%M:%S"

    @model_validator(mode="after")
    def validate_production_security(self) -> "Settings":
        if self.APP_ENV != "production":
            return self
        if self.SECRET_KEY == self.DEVELOPMENT_SECRET_KEY or len(self.SECRET_KEY) < 32:
            raise ValueError("生产环境必须通过 SECRET_KEY 注入至少 32 字符的独立密钥")
        if "*" in self.CORS_ORIGINS:
            raise ValueError("生产环境 CORS_ORIGINS 禁止使用通配符")
        if self.BOOTSTRAP_ADMIN_ENABLED and not self.BOOTSTRAP_ADMIN_PASSWORD:
            raise ValueError("启用管理员初始化时必须配置 BOOTSTRAP_ADMIN_PASSWORD")
        return self


settings = Settings()
