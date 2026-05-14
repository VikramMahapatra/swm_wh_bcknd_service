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


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    return Settings()
