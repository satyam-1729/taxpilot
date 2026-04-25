from functools import lru_cache
from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    app_env: str = Field(default="dev")
    app_secret: str = Field(default="change-me-in-prod", description="HMAC key for our session JWT")

    database_url: str = Field(default="postgresql+asyncpg://taxpilot:taxpilot@localhost:5432/taxpilot")
    redis_url: str = Field(default="redis://localhost:6379/0")

    firebase_service_account_path: str = Field(default="./firebase-service-account.json")
    firebase_project_id: str = Field(default="")

    field_encryption_key: str = Field(
        default="dev-key-change-me-please-32-bytes!",
        description="32-byte key used for encrypting PAN/Aadhaar at rest",
    )

    session_ttl_seconds: int = Field(default=60 * 60 * 24 * 30)  # 30 days

    cors_origins: list[str] = Field(default_factory=lambda: ["http://localhost:4200"])


@lru_cache
def get_settings() -> Settings:
    return Settings()
