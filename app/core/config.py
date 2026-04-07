from functools import lru_cache

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8")

    app_name: str = Field(default="Fitness Hub", alias="APP_NAME")
    app_env: str = Field(default="development", alias="APP_ENV")
    app_host: str = Field(default="127.0.0.1", alias="APP_HOST")
    app_port: int = Field(default=8000, alias="APP_PORT")
    app_base_url: str = Field(default="http://127.0.0.1:8000", alias="APP_BASE_URL")
    canonical_timezone: str = Field(
        default="America/Indiana/Indianapolis", alias="CANONICAL_TIMEZONE"
    )
    database_url: str = Field(
        default="sqlite:///./fitness.db",
        alias="DATABASE_URL",
    )
    enable_scheduler: bool = Field(default=True, alias="ENABLE_SCHEDULER")
    internal_sync_token: str = Field(default="change-me", alias="INTERNAL_SYNC_TOKEN")
    default_backfill_days: int = Field(default=90, alias="DEFAULT_BACKFILL_DAYS")
    enable_whoop_webhooks: bool = Field(default=False, alias="ENABLE_WHOOP_WEBHOOKS")

    whoop_client_id: str | None = Field(default=None, alias="WHOOP_CLIENT_ID")
    whoop_client_secret: str | None = Field(default=None, alias="WHOOP_CLIENT_SECRET")
    whoop_redirect_uri: str | None = Field(default=None, alias="WHOOP_REDIRECT_URI")
    whoop_webhook_secret: str | None = Field(default=None, alias="WHOOP_WEBHOOK_SECRET")

    hevy_api_key: str | None = Field(default=None, alias="HEVY_API_KEY")

    mfp_bridge_shared_token: str = Field(
        default="change-me", alias="MFP_BRIDGE_SHARED_TOKEN"
    )
    mfp_cookie_header: str | None = Field(default=None, alias="MFP_COOKIE_HEADER")
    mfp_cookie_file: str | None = Field(default=None, alias="MFP_COOKIE_FILE")
    mfp_bridge_base_url: str = Field(
        default="http://127.0.0.1:8000", alias="MFP_BRIDGE_BASE_URL"
    )
    mfp_backfill_days: int = Field(default=90, alias="MFP_BACKFILL_DAYS")
    mfp_sync_window_days: int = Field(default=3, alias="MFP_SYNC_WINDOW_DAYS")


@lru_cache
def get_settings() -> Settings:
    return Settings()
