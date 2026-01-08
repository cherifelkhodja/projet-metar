"""METAR observation entity."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from decimal import Decimal
from typing import Any, Self

from ..value_objects import (
    CloudLayer,
    FlightCategory,
    ICAOCode,
    Visibility,
    WeatherPhenomenon,
    Wind,
)


@dataclass
class MetarObservation:
    """Represents a parsed METAR observation.

    This is the primary entity for storing weather data.
    """

    icao_code: ICAOCode
    observation_time: datetime
    raw_metar: str
    source: str

    # Wind data
    wind: Wind | None = None

    # Visibility
    visibility: Visibility | None = None

    # Weather phenomena
    weather_phenomena: list[WeatherPhenomenon] = field(default_factory=list)

    # Cloud layers
    cloud_layers: list[CloudLayer] = field(default_factory=list)

    # Temperature
    temperature_c: Decimal | None = None
    dewpoint_c: Decimal | None = None

    # Pressure
    altimeter_inhg: Decimal | None = None
    altimeter_hpa: int | None = None

    # Calculated fields
    flight_category: FlightCategory | None = None

    # Metadata
    id: int | None = None
    fetched_at: datetime = field(default_factory=datetime.utcnow)

    def __post_init__(self) -> None:
        """Validate and calculate derived fields."""
        if isinstance(self.icao_code, str):
            self.icao_code = ICAOCode(self.icao_code)

        # Calculate flight category if not set
        if self.flight_category is None:
            self.flight_category = FlightCategory.calculate(
                self.visibility,
                self.cloud_layers,
            )

    @classmethod
    def create(
        cls,
        icao_code: str | ICAOCode,
        observation_time: datetime,
        raw_metar: str,
        source: str,
        **kwargs: Any,
    ) -> Self:
        """Factory method to create a new MetarObservation."""
        if isinstance(icao_code, str):
            icao_code = ICAOCode(icao_code)

        return cls(
            icao_code=icao_code,
            observation_time=observation_time,
            raw_metar=raw_metar,
            source=source,
            **kwargs,
        )

    @property
    def icao(self) -> str:
        """Return the ICAO code as a string."""
        return str(self.icao_code)

    @property
    def ceiling_ft(self) -> int | None:
        """Return the ceiling height in feet (lowest BKN/OVC/VV layer)."""
        for layer in self.cloud_layers:
            if layer.coverage.is_ceiling and layer.altitude_ft is not None:
                return layer.altitude_ft
        return None

    @property
    def wind_direction_degrees(self) -> int | None:
        """Return wind direction in degrees."""
        return self.wind.direction_degrees if self.wind else None

    @property
    def wind_speed_kt(self) -> int | None:
        """Return wind speed in knots."""
        return self.wind.speed_kt if self.wind else None

    @property
    def wind_gust_kt(self) -> int | None:
        """Return gust speed in knots."""
        return self.wind.gust_kt if self.wind else None

    @property
    def visibility_statute_mi(self) -> Decimal | None:
        """Return visibility in statute miles."""
        return self.visibility.statute_miles if self.visibility else None

    @property
    def visibility_meters(self) -> int | None:
        """Return visibility in meters."""
        return self.visibility.meters if self.visibility else None

    @property
    def flight_category_str(self) -> str | None:
        """Return flight category as string."""
        return str(self.flight_category) if self.flight_category else None

    @property
    def has_significant_weather(self) -> bool:
        """Check if there are significant weather phenomena."""
        return len(self.weather_phenomena) > 0

    @property
    def has_thunderstorm(self) -> bool:
        """Check if there is thunderstorm activity."""
        return any(wp.is_thunderstorm for wp in self.weather_phenomena)

    @property
    def has_precipitation(self) -> bool:
        """Check if there is precipitation."""
        return any(wp.is_precipitation for wp in self.weather_phenomena)

    def weather_phenomena_to_json(self) -> list[dict[str, Any]]:
        """Convert weather phenomena to JSON-serializable format."""
        return [wp.to_dict() for wp in self.weather_phenomena]

    def cloud_layers_to_json(self) -> list[dict[str, Any]]:
        """Convert cloud layers to JSON-serializable format."""
        return [cl.to_dict() for cl in self.cloud_layers]

    def __eq__(self, other: object) -> bool:
        """Check equality based on ICAO code and observation time."""
        if isinstance(other, MetarObservation):
            return (
                self.icao_code == other.icao_code
                and self.observation_time == other.observation_time
            )
        return False

    def __hash__(self) -> int:
        """Return hash based on ICAO code and observation time."""
        return hash((self.icao_code, self.observation_time))

    def __str__(self) -> str:
        """Return string representation (raw METAR)."""
        return self.raw_metar
