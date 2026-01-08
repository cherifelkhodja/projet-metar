"""Wind data value object."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Self


@dataclass(frozen=True, slots=True)
class Wind:
    """Represents wind conditions from a METAR observation.

    Attributes:
        direction_degrees: Wind direction in degrees (0-360), None for variable/calm
        speed_kt: Wind speed in knots
        gust_kt: Gust speed in knots, if any
        variable_from: Variable wind direction start (degrees)
        variable_to: Variable wind direction end (degrees)
        is_calm: True if wind is calm (00000KT)
        is_variable: True if wind direction is variable (VRB)
    """

    direction_degrees: int | None
    speed_kt: int
    gust_kt: int | None = None
    variable_from: int | None = None
    variable_to: int | None = None
    is_calm: bool = False
    is_variable: bool = False

    def __post_init__(self) -> None:
        """Validate wind data."""
        if self.speed_kt < 0:
            raise ValueError(f"Wind speed cannot be negative: {self.speed_kt}")

        if self.gust_kt is not None and self.gust_kt < 0:
            raise ValueError(f"Gust speed cannot be negative: {self.gust_kt}")

        if self.gust_kt is not None and self.gust_kt <= self.speed_kt:
            raise ValueError(
                f"Gust speed ({self.gust_kt}) must be greater than wind speed ({self.speed_kt})"
            )

        if self.direction_degrees is not None and not 0 <= self.direction_degrees <= 360:
            raise ValueError(
                f"Wind direction must be between 0 and 360: {self.direction_degrees}"
            )

    @classmethod
    def calm(cls) -> Self:
        """Create a calm wind condition."""
        return cls(direction_degrees=None, speed_kt=0, is_calm=True)

    @classmethod
    def variable(cls, speed_kt: int, gust_kt: int | None = None) -> Self:
        """Create a variable wind condition."""
        return cls(
            direction_degrees=None,
            speed_kt=speed_kt,
            gust_kt=gust_kt,
            is_variable=True,
        )

    @property
    def speed_mps(self) -> float:
        """Return wind speed in meters per second."""
        return self.speed_kt * 0.514444

    @property
    def speed_kmh(self) -> float:
        """Return wind speed in kilometers per hour."""
        return self.speed_kt * 1.852

    @property
    def has_gusts(self) -> bool:
        """Check if there are gusts reported."""
        return self.gust_kt is not None

    @property
    def has_variable_direction(self) -> bool:
        """Check if wind direction varies."""
        return self.variable_from is not None and self.variable_to is not None

    def __str__(self) -> str:
        """Return a human-readable representation."""
        if self.is_calm:
            return "Calm"
        if self.is_variable:
            result = f"Variable at {self.speed_kt}kt"
        else:
            result = f"{self.direction_degrees:03d}° at {self.speed_kt}kt"
        if self.gust_kt:
            result += f" gusting {self.gust_kt}kt"
        if self.has_variable_direction:
            result += f" (varying {self.variable_from}°-{self.variable_to}°)"
        return result
