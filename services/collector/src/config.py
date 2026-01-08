"""Configuration management for the collector service."""

from __future__ import annotations

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
    )

    # Database
    database_url: str = Field(
        default="postgresql+asyncpg://metar_user:metar_password@localhost:5432/metar_db",
        description="PostgreSQL connection URL",
    )

    # Collection
    collection_interval_minutes: int = Field(
        default=60,
        description="Interval between collection runs in minutes",
    )
    collection_timeout_seconds: float = Field(
        default=30.0,
        description="Timeout for HTTP requests",
    )
    collection_retry_attempts: int = Field(
        default=3,
        description="Number of retry attempts for failed requests",
    )
    collection_retry_delay_seconds: float = Field(
        default=5.0,
        description="Base delay between retries",
    )

    # Sources
    noaa_awc_base_url: str = Field(
        default="https://aviationweather.gov/api/data/metar",
        description="NOAA AWC API base URL",
    )
    checkwx_api_key: str | None = Field(
        default=None,
        description="CheckWX API key (optional)",
    )
    checkwx_base_url: str = Field(
        default="https://api.checkwx.com/metar",
        description="CheckWX API base URL",
    )
    primary_source: str = Field(
        default="noaa_awc",
        description="Primary METAR data source",
    )

    # Paths
    airports_config_path: str = Field(
        default="/app/config/airports.yaml",
        description="Path to airports configuration file",
    )

    # Logging
    log_level: str = Field(
        default="INFO",
        description="Logging level",
    )
    log_format: str = Field(
        default="json",
        description="Log format (json or console)",
    )


def get_settings() -> Settings:
    """Get application settings."""
    return Settings()
