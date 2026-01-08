"""ICAO airport code value object."""

from __future__ import annotations

import re
from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class ICAOCode:
    """Represents a valid ICAO airport code.

    ICAO codes are 4-letter identifiers for airports worldwide.
    Examples: LFPG (Paris CDG), KJFK (New York JFK), EGLL (London Heathrow)
    """

    value: str

    _ICAO_PATTERN: re.Pattern[str] = re.compile(r"^[A-Z]{4}$")

    def __post_init__(self) -> None:
        """Validate the ICAO code format."""
        normalized = self.value.upper().strip()
        if not self._ICAO_PATTERN.match(normalized):
            raise ValueError(
                f"Invalid ICAO code: '{self.value}'. Must be exactly 4 uppercase letters."
            )
        # Use object.__setattr__ because dataclass is frozen
        object.__setattr__(self, "value", normalized)

    def __str__(self) -> str:
        """Return the string representation."""
        return self.value

    def __eq__(self, other: object) -> bool:
        """Check equality with another ICAOCode or string."""
        if isinstance(other, ICAOCode):
            return self.value == other.value
        if isinstance(other, str):
            return self.value == other.upper()
        return False

    def __hash__(self) -> int:
        """Return hash for use in sets and dicts."""
        return hash(self.value)

    @classmethod
    def from_string(cls, code: str) -> ICAOCode:
        """Create an ICAOCode from a string."""
        return cls(value=code)
