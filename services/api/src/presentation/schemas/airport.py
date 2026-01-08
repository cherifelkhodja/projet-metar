"""Airport-related schemas."""

from __future__ import annotations

from datetime import datetime
from decimal import Decimal

from pydantic import BaseModel, Field, field_validator


class AirportCreate(BaseModel):
    """Schema for creating a new airport."""

    icao_code: str = Field(
        ...,
        min_length=4,
        max_length=4,
        description="ICAO airport code (4 letters)",
        json_schema_extra={"example": "LFPG"},
    )
    name: str | None = Field(
        None,
        max_length=255,
        description="Airport name",
        json_schema_extra={"example": "Paris Charles de Gaulle Airport"},
    )
    latitude: Decimal | None = Field(
        None,
        ge=-90,
        le=90,
        description="Latitude in decimal degrees",
        json_schema_extra={"example": 49.0097},
    )
    longitude: Decimal | None = Field(
        None,
        ge=-180,
        le=180,
        description="Longitude in decimal degrees",
        json_schema_extra={"example": 2.5478},
    )
    elevation_ft: int | None = Field(
        None,
        description="Elevation in feet",
        json_schema_extra={"example": 392},
    )
    timezone: str | None = Field(
        None,
        max_length=50,
        description="Timezone identifier",
        json_schema_extra={"example": "Europe/Paris"},
    )

    @field_validator("icao_code")
    @classmethod
    def validate_icao(cls, v: str) -> str:
        """Validate and normalize ICAO code."""
        v = v.upper().strip()
        if not v.isalpha():
            raise ValueError("ICAO code must contain only letters")
        return v


class AirportResponse(BaseModel):
    """Schema for airport response."""

    icao_code: str = Field(..., description="ICAO airport code")
    name: str | None = Field(None, description="Airport name")
    latitude: Decimal | None = Field(None, description="Latitude")
    longitude: Decimal | None = Field(None, description="Longitude")
    elevation_ft: int | None = Field(None, description="Elevation in feet")
    timezone: str | None = Field(None, description="Timezone")
    is_active: bool = Field(..., description="Whether airport is actively monitored")
    created_at: datetime = Field(..., description="Creation timestamp")
    updated_at: datetime = Field(..., description="Last update timestamp")

    model_config = {"from_attributes": True}


class AirportListResponse(BaseModel):
    """Schema for list of airports."""

    airports: list[AirportResponse]
    total: int = Field(..., description="Total number of airports")
