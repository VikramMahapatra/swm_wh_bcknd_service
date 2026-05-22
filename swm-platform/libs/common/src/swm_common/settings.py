from functools import lru_cache

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    env: str = Field(default="dev", alias="ENV")
    log_level: str = Field(default="INFO", alias="LOG_LEVEL")
    metrics_enabled: bool = Field(default=True, alias="METRICS_ENABLED")

    ingestion_api_host: str = Field(default="0.0.0.0", alias="INGESTION_API_HOST")  # noqa: S104
    ingestion_api_port: int = Field(default=8001, alias="INGESTION_API_PORT")
    websocket_api_host: str = Field(default="0.0.0.0", alias="WEBSOCKET_API_HOST")  # noqa: S104
    websocket_api_port: int = Field(default=8002, alias="WEBSOCKET_API_PORT")
    admin_api_host: str = Field(default="0.0.0.0", alias="ADMIN_API_HOST")  # noqa: S104
    admin_api_port: int = Field(default=8003, alias="ADMIN_API_PORT")

    postgres_dsn: str = Field(alias="POSTGRES_DSN")
    postgres_sslmode: str = Field(default="require", alias="POSTGRES_SSLMODE")

    clickhouse_host: str = Field(default="localhost", alias="CLICKHOUSE_HOST")
    clickhouse_port: int = Field(default=8123, alias="CLICKHOUSE_PORT")
    clickhouse_db: str = Field(default="default", alias="CLICKHOUSE_DB")
    clickhouse_user: str = Field(default="default", alias="CLICKHOUSE_USER")
    clickhouse_password: str = Field(default="", alias="CLICKHOUSE_PASSWORD")
    clickhouse_dsn: str = Field(alias="CLICKHOUSE_DSN")

    redis_url: str = Field(alias="REDIS_URL")
    redis_max_connections: int = Field(default=200, alias="REDIS_MAX_CONNECTIONS")
    redis_socket_timeout: float = Field(default=5.0, alias="REDIS_SOCKET_TIMEOUT")
    redis_socket_connect_timeout: float = Field(default=3.0, alias="REDIS_SOCKET_CONNECT_TIMEOUT")
    redis_retry_attempts: int = Field(default=5, alias="REDIS_RETRY_ATTEMPTS")
    redis_retry_base_delay: float = Field(default=0.05, alias="REDIS_RETRY_BASE_DELAY")

    jwt_secret: str = Field(alias="JWT_SECRET")
    jwt_algorithm: str = Field(default="HS256", alias="JWT_ALGORITHM")
    jwt_expiry_minutes: int = Field(default=30, alias="JWT_EXPIRY_MINUTES")

    auth_enforce_jwt: bool = Field(default=False, alias="AUTH_ENFORCE_JWT")
    auth_allow_legacy_role_header: bool = Field(default=True, alias="AUTH_ALLOW_LEGACY_ROLE_HEADER")
    auth_legacy_default_role: str = Field(default="admin", alias="AUTH_LEGACY_DEFAULT_ROLE")
    auth_api_keys_json: str = Field(default="[]", alias="AUTH_API_KEYS_JSON")
    auth_users_json: str = Field(default="[]", alias="AUTH_USERS_JSON")

    ingestion_webhook_auth_enabled: bool = Field(default=False, alias="INGESTION_WEBHOOK_AUTH_ENABLED")
    ingestion_webhook_secret: str = Field(default="", alias="INGESTION_WEBHOOK_SECRET")
    ingestion_webhook_secret_header: str = Field(
        default="X-Webhook-Secret",
        alias="INGESTION_WEBHOOK_SECRET_HEADER",
    )
    ingestion_webhook_hmac_secret: str = Field(default="", alias="INGESTION_WEBHOOK_HMAC_SECRET")
    ingestion_webhook_signature_header: str = Field(
        default="X-Webhook-Signature",
        alias="INGESTION_WEBHOOK_SIGNATURE_HEADER",
    )
    ingestion_webhook_allowed_ips: str = Field(default="", alias="INGESTION_WEBHOOK_ALLOWED_IPS")
    ingestion_webhook_nonce_ttl_seconds: int = Field(default=0, alias="INGESTION_WEBHOOK_NONCE_TTL_SECONDS")
    ingestion_webhook_nonce_header: str = Field(default="X-Webhook-Nonce", alias="INGESTION_WEBHOOK_NONCE_HEADER")
    ingestion_webhook_vendor_header: str = Field(default="X-Vendor-Id", alias="INGESTION_WEBHOOK_VENDOR_HEADER")

    ingestion_rate_limit_enabled: bool = Field(default=False, alias="INGESTION_RATE_LIMIT_ENABLED")
    ingestion_rate_limit_prefix: str = Field(default="rl:ingestion", alias="INGESTION_RATE_LIMIT_PREFIX")
    ingestion_rate_limit_global_limit: int = Field(default=2000, alias="INGESTION_RATE_LIMIT_GLOBAL_LIMIT")
    ingestion_rate_limit_global_window_seconds: int = Field(
        default=60,
        alias="INGESTION_RATE_LIMIT_GLOBAL_WINDOW_SECONDS",
    )
    ingestion_rate_limit_vendor_limit: int = Field(default=1000, alias="INGESTION_RATE_LIMIT_VENDOR_LIMIT")
    ingestion_rate_limit_vendor_window_seconds: int = Field(
        default=60,
        alias="INGESTION_RATE_LIMIT_VENDOR_WINDOW_SECONDS",
    )
    ingestion_rate_limit_ip_limit: int = Field(default=400, alias="INGESTION_RATE_LIMIT_IP_LIMIT")
    ingestion_rate_limit_ip_window_seconds: int = Field(default=60, alias="INGESTION_RATE_LIMIT_IP_WINDOW_SECONDS")
    ingestion_rate_limit_imei_limit: int = Field(default=180, alias="INGESTION_RATE_LIMIT_IMEI_LIMIT")
    ingestion_rate_limit_imei_window_seconds: int = Field(
        default=60,
        alias="INGESTION_RATE_LIMIT_IMEI_WINDOW_SECONDS",
    )

    websocket_auth_required: bool = Field(default=False, alias="WEBSOCKET_AUTH_REQUIRED")


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    return Settings()
