"""Centralized application configuration loaded from environment variables."""

from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_ignore_empty=True,
        extra="ignore",
    )

    # Application
    app_name: str = "App"
    environment: str = "development"
    debug: bool = True
    api_prefix: str = "/api/v1"
    # Must equal the version at the top of context/API_CONTRACT.md — asserted on the
    # frontend at boot (`GET /meta/enums`).
    contract_version: str = "v1.4.0"
    host: str = "0.0.0.0"
    port: int = 8001

    # Database
    database_url: str = "postgresql+psycopg://postgres:postgres@localhost:5432/app"

    # JWT
    jwt_secret: str = "change-me-to-a-long-random-string"
    jwt_algorithm: str = "HS256"
    jwt_access_token_expire_minutes: int = 30
    jwt_refresh_token_expire_days: int = 7

    # CORS (comma-separated origins)
    cors_origins: str = "http://localhost:3001"

    # Logging
    log_level: str = "INFO"

    # Files
    upload_dir: str = "uploads"

    # Redis / task queue (Dramatiq)
    redis_url: str = "redis://localhost:6379/0"

    # Rate limiting (in-memory, per IP + per account)
    rate_limit_enabled: bool = True
    rate_limit_requests: int = 100
    rate_limit_window_seconds: int = 60

    # MinIO / object storage
    minio_endpoint: str = "localhost:9000"
    minio_access_key: str = "minioadmin"
    minio_secret_key: str = "minioadmin"
    minio_bucket: str = "dealflow360"
    minio_secure: bool = False

    # URLs
    frontend_url: str = "http://localhost:3001"

    # Seed admin user
    admin_email: str = "admin@example.com"
    admin_password: str = "admin12345"

    @property
    def cors_origins_list(self) -> list[str]:
        return [origin.strip() for origin in self.cors_origins.split(",") if origin.strip()]

    @property
    def is_production(self) -> bool:
        return self.environment == "production"


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
