"""METAR-related schemas."""

from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from typing import Any

from pydantic import BaseModel, Field


class WindData(BaseModel):
    """Wind information from METAR."""

    direction_degrees: int | None = Field(None, description="Wind direction in degrees")
    speed_kt: int | None = Field(None, description="Wind speed in knots")
    gust_kt: int | None = Field(None, description="Gust speed in knots")
    variable_from: int | None = Field(None, description="Variable direction start")
    variable_to: int | None = Field(None, description="Variable direction end")
    is_calm: bool = Field(False, description="Whether wind is calm")
    is_variable: bool = Field(False, description="Whether direction is variable")


class CloudLayerData(BaseModel):
    """Cloud layer information."""

    coverage: str = Field(..., description="Cloud coverage type (FEW, SCT, BKN, OVC, etc.)")
    altitude_ft: int | None = Field(None, description="Cloud base altitude in feet AGL")
    cloud_type: str | None = Field(None, description="Cloud type (CB, TCU)")


class WeatherPhenomenonData(BaseModel):
    """Weather phenomenon information."""

    raw: str = Field(..., description="Raw weather code")
    intensity: str = Field(..., description="Intensity (-, moderate, +, VC)")
    descriptor: str | None = Field(None, description="Descriptor code")
    phenomena: list[str] = Field(default_factory=list, description="Phenomenon codes")


class MetarResponse(BaseModel):
    """Schema for METAR observation response."""

    id: int = Field(..., description="Observation ID")
    icao_code: str = Field(..., description="ICAO airport code")
    observation_time: datetime = Field(..., description="Observation timestamp (UTC)")
    raw_metar: str = Field(..., description="Raw METAR string")

    # Wind
    wind: WindData | None = Field(None, description="Wind information")

    # Visibility
    visibility_statute_mi: Decimal | None = Field(None, description="Visibility in statute miles")
    visibility_meters: int | None = Field(None, description="Visibility in meters")

    # Weather
    weather_phenomena: list[WeatherPhenomenonData] = Field(
        default_factory=list,
        description="Weather phenomena",
    )

    # Clouds
    cloud_layers: list[CloudLayerData] = Field(
        default_factory=list,
        description="Cloud layers",
    )
    ceiling_ft: int | None = Field(None, description="Ceiling height in feet")

    # Temperature
    temperature_c: Decimal | None = Field(None, description="Temperature in Celsius")
    dewpoint_c: Decimal | None = Field(None, description="Dewpoint in Celsius")

    # Pressure
    altimeter_inhg: Decimal | None = Field(None, description="Altimeter in inches of mercury")
    altimeter_hpa: int | None = Field(None, description="Altimeter in hectopascals")

    # Flight category
    flight_category: str | None = Field(None, description="Flight category (VFR, MVFR, IFR, LIFR)")

    # Metadata
    source: str = Field(..., description="Data source")
    fetched_at: datetime = Field(..., description="When data was fetched")

    model_config = {"from_attributes": True}

    @classmethod
    def from_model(cls, model: Any) -> MetarResponse:
        """Create from ORM model."""
        wind = None
        if model.wind_speed_kt is not None:
            wind = WindData(
                direction_degrees=model.wind_direction_degrees,
                speed_kt=model.wind_speed_kt,
                gust_kt=model.wind_gust_kt,
                variable_from=model.wind_variable_from,
                variable_to=model.wind_variable_to,
                is_calm=model.wind_speed_kt == 0 and model.wind_direction_degrees is None,
                is_variable=model.wind_direction_degrees is None and model.wind_speed_kt > 0,
            )

        weather = [
            WeatherPhenomenonData(**wp)
            for wp in (model.weather_phenomena or [])
            if isinstance(wp, dict)
        ]

        clouds = [
            CloudLayerData(**cl)
            for cl in (model.cloud_layers or [])
            if isinstance(cl, dict)
        ]

        return cls(
            id=model.id,
            icao_code=model.icao_code,
            observation_time=model.observation_time,
            raw_metar=model.raw_metar,
            wind=wind,
            visibility_statute_mi=model.visibility_statute_mi,
            visibility_meters=model.visibility_meters,
            weather_phenomena=weather,
            cloud_layers=clouds,
            ceiling_ft=model.ceiling_ft,
            temperature_c=model.temperature_c,
            dewpoint_c=model.dewpoint_c,
            altimeter_inhg=model.altimeter_inhg,
            altimeter_hpa=model.altimeter_hpa,
            flight_category=model.flight_category,
            source=model.source,
            fetched_at=model.fetched_at,
        )


class MetarHistoryResponse(BaseModel):
    """Schema for METAR history response."""

    icao_code: str = Field(..., description="ICAO airport code")
    observations: list[MetarResponse] = Field(..., description="METAR observations")
    total: int = Field(..., description="Total observations")
    page: int = Field(..., description="Current page")
    per_page: int = Field(..., description="Items per page")
    pages: int = Field(..., description="Total pages")


class MetarBulkResponse(BaseModel):
    """Schema for bulk METAR response."""

    observations: list[MetarResponse] = Field(..., description="Latest METARs")
    count: int = Field(..., description="Number of observations")
