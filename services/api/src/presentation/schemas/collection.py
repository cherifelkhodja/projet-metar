"""Collection-related schemas."""

from __future__ import annotations

from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field


class CollectionLogResponse(BaseModel):
    """Schema for collection log response."""

    id: int = Field(..., description="Log ID")
    started_at: datetime = Field(..., description="Collection start time")
    completed_at: datetime | None = Field(None, description="Collection end time")
    status: str = Field(..., description="Collection status")
    airports_requested: int = Field(..., description="Number of airports requested")
    airports_success: int = Field(..., description="Successful collections")
    airports_failed: int = Field(..., description="Failed collections")
    new_observations: int = Field(..., description="New observations stored")
    duplicates_skipped: int = Field(..., description="Duplicates skipped")
    error_message: str | None = Field(None, description="Error message if failed")
    details: dict[str, Any] = Field(default_factory=dict, description="Additional details")

    model_config = {"from_attributes": True}

    @property
    def duration_seconds(self) -> float | None:
        """Calculate duration in seconds."""
        if self.completed_at and self.started_at:
            return (self.completed_at - self.started_at).total_seconds()
        return None


class CollectionStatusResponse(BaseModel):
    """Schema for collection status response."""

    last_collection: CollectionLogResponse | None = Field(
        None,
        description="Last collection log",
    )
    is_running: bool = Field(..., description="Whether collection is currently running")
    next_scheduled: datetime | None = Field(
        None,
        description="Next scheduled collection time",
    )
