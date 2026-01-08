"""Metrics-related schemas."""

from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, Field


class MetricsResponse(BaseModel):
    """Schema for metrics response."""

    # Database stats
    total_airports: int = Field(..., description="Total airports in database")
    active_airports: int = Field(..., description="Active airports being monitored")
    total_observations: int = Field(..., description="Total METAR observations")

    # Collection stats
    total_collections: int = Field(..., description="Total collection runs")
    successful_collections: int = Field(..., description="Successful collection runs")
    failed_collections: int = Field(..., description="Failed collection runs")
    avg_observations_per_run: float = Field(
        ...,
        description="Average observations per run",
    )

    # Time info
    oldest_observation: datetime | None = Field(
        None,
        description="Oldest observation timestamp",
    )
    newest_observation: datetime | None = Field(
        None,
        description="Newest observation timestamp",
    )

    # System info
    uptime_seconds: float | None = Field(None, description="Service uptime in seconds")
