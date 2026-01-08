"""Configuration management for the API service."""

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

    # API
    api_host: str = Field(
        default="0.0.0.0",
        description="API host address",
    )
    api_port: int = Field(
        default=8000,
        description="API port",
    )
    api_workers: int = Field(
        default=2,
        description="Number of API workers",
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

    # CORS
    cors_origins: list[str] = Field(
        default=["*"],
        description="Allowed CORS origins",
    )


def get_settings() -> Settings:
    """Get application settings."""
    return Settings()
