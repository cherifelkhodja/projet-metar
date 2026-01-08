"""Airport entity."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from decimal import Decimal
from typing import Self

from ..value_objects import ICAOCode


@dataclass
class Airport:
    """Represents an airport being monitored for METAR data.

    This is the aggregate root for airport-related operations.
    """

    icao_code: ICAOCode
    name: str | None = None
    latitude: Decimal | None = None
    longitude: Decimal | None = None
    elevation_ft: int | None = None
    timezone: str | None = None
    is_active: bool = True
    created_at: datetime = field(default_factory=datetime.utcnow)
    updated_at: datetime = field(default_factory=datetime.utcnow)

    def __post_init__(self) -> None:
        """Validate airport data."""
        if isinstance(self.icao_code, str):
            self.icao_code = ICAOCode(self.icao_code)

        if self.latitude is not None:
            if not -90 <= self.latitude <= 90:
                raise ValueError(f"Latitude must be between -90 and 90: {self.latitude}")

        if self.longitude is not None:
            if not -180 <= self.longitude <= 180:
                raise ValueError(f"Longitude must be between -180 and 180: {self.longitude}")

    @classmethod
    def create(
        cls,
        icao_code: str | ICAOCode,
        name: str | None = None,
        latitude: Decimal | float | None = None,
        longitude: Decimal | float | None = None,
        elevation_ft: int | None = None,
        timezone: str | None = None,
    ) -> Self:
        """Factory method to create a new Airport."""
        if isinstance(icao_code, str):
            icao_code = ICAOCode(icao_code)

        lat = Decimal(str(latitude)) if latitude is not None else None
        lon = Decimal(str(longitude)) if longitude is not None else None

        return cls(
            icao_code=icao_code,
            name=name,
            latitude=lat,
            longitude=lon,
            elevation_ft=elevation_ft,
            timezone=timezone,
        )

    def activate(self) -> None:
        """Activate the airport for monitoring."""
        self.is_active = True
        self.updated_at = datetime.utcnow()

    def deactivate(self) -> None:
        """Deactivate the airport from monitoring."""
        self.is_active = False
        self.updated_at = datetime.utcnow()

    def update_location(
        self,
        latitude: Decimal | float,
        longitude: Decimal | float,
        elevation_ft: int | None = None,
    ) -> None:
        """Update the airport's geographic location."""
        self.latitude = Decimal(str(latitude))
        self.longitude = Decimal(str(longitude))
        if elevation_ft is not None:
            self.elevation_ft = elevation_ft
        self.updated_at = datetime.utcnow()

    @property
    def icao(self) -> str:
        """Return the ICAO code as a string."""
        return str(self.icao_code)

    def __eq__(self, other: object) -> bool:
        """Check equality based on ICAO code."""
        if isinstance(other, Airport):
            return self.icao_code == other.icao_code
        return False

    def __hash__(self) -> int:
        """Return hash based on ICAO code."""
        return hash(self.icao_code)

    def __str__(self) -> str:
        """Return string representation."""
        if self.name:
            return f"{self.icao} - {self.name}"
        return self.icao
