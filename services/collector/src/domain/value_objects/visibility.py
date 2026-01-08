"""Visibility value object."""

from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal
from typing import Self


@dataclass(frozen=True, slots=True)
class Visibility:
    """Represents visibility conditions from a METAR observation.

    Stores visibility in both statute miles (US) and meters (ICAO).
    """

    statute_miles: Decimal | None = None
    meters: int | None = None
    is_greater_than: bool = False  # For "P6SM" or ">10000m"

    def __post_init__(self) -> None:
        """Validate visibility data."""
        if self.statute_miles is None and self.meters is None:
            raise ValueError("At least one visibility value must be provided")

        if self.statute_miles is not None and self.statute_miles < 0:
            raise ValueError(f"Visibility cannot be negative: {self.statute_miles} SM")

        if self.meters is not None and self.meters < 0:
            raise ValueError(f"Visibility cannot be negative: {self.meters} m")

    @classmethod
    def from_statute_miles(cls, miles: Decimal | float, is_greater_than: bool = False) -> Self:
        """Create visibility from statute miles."""
        miles_decimal = Decimal(str(miles))
        meters = int(miles_decimal * Decimal("1609.34"))
        return cls(
            statute_miles=miles_decimal,
            meters=meters,
            is_greater_than=is_greater_than,
        )

    @classmethod
    def from_meters(cls, meters: int, is_greater_than: bool = False) -> Self:
        """Create visibility from meters."""
        statute_miles = Decimal(str(meters)) / Decimal("1609.34")
        return cls(
            statute_miles=statute_miles.quantize(Decimal("0.01")),
            meters=meters,
            is_greater_than=is_greater_than,
        )

    @classmethod
    def unlimited(cls) -> Self:
        """Create unlimited visibility (CAVOK or P6SM)."""
        return cls.from_statute_miles(Decimal("10"), is_greater_than=True)

    @property
    def statute_miles_float(self) -> float | None:
        """Return statute miles as float."""
        return float(self.statute_miles) if self.statute_miles else None

    @property
    def is_low(self) -> bool:
        """Check if visibility is low (below 3 SM / 5000m)."""
        if self.statute_miles is not None:
            return self.statute_miles < Decimal("3")
        if self.meters is not None:
            return self.meters < 5000
        return False

    @property
    def is_very_low(self) -> bool:
        """Check if visibility is very low (below 1 SM / 1600m)."""
        if self.statute_miles is not None:
            return self.statute_miles < Decimal("1")
        if self.meters is not None:
            return self.meters < 1600
        return False

    def __str__(self) -> str:
        """Return a human-readable representation."""
        prefix = ">" if self.is_greater_than else ""
        if self.statute_miles is not None:
            return f"{prefix}{self.statute_miles} SM"
        if self.meters is not None:
            return f"{prefix}{self.meters} m"
        return "Unknown"
