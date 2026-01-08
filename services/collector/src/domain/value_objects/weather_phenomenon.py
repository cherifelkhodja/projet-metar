"""Weather phenomenon value object."""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum


class WeatherIntensity(Enum):
    """Intensity of weather phenomena."""

    LIGHT = "-"
    MODERATE = ""  # No prefix means moderate
    HEAVY = "+"
    VICINITY = "VC"  # In vicinity (5-10 miles)

    @property
    def description(self) -> str:
        """Return human-readable description."""
        descriptions = {
            WeatherIntensity.LIGHT: "Light",
            WeatherIntensity.MODERATE: "Moderate",
            WeatherIntensity.HEAVY: "Heavy",
            WeatherIntensity.VICINITY: "In Vicinity",
        }
        return descriptions[self]


# Weather phenomenon codes as defined in METAR
WEATHER_DESCRIPTORS = {
    "MI": "Shallow",
    "PR": "Partial",
    "BC": "Patches",
    "DR": "Low Drifting",
    "BL": "Blowing",
    "SH": "Showers",
    "TS": "Thunderstorm",
    "FZ": "Freezing",
}

WEATHER_PRECIPITATION = {
    "DZ": "Drizzle",
    "RA": "Rain",
    "SN": "Snow",
    "SG": "Snow Grains",
    "IC": "Ice Crystals",
    "PL": "Ice Pellets",
    "GR": "Hail",
    "GS": "Small Hail",
    "UP": "Unknown Precipitation",
}

WEATHER_OBSCURATION = {
    "BR": "Mist",
    "FG": "Fog",
    "FU": "Smoke",
    "VA": "Volcanic Ash",
    "DU": "Dust",
    "SA": "Sand",
    "HZ": "Haze",
    "PY": "Spray",
}

WEATHER_OTHER = {
    "PO": "Dust/Sand Whirls",
    "SQ": "Squalls",
    "FC": "Funnel Cloud",
    "SS": "Sandstorm",
    "DS": "Duststorm",
}

ALL_WEATHER_CODES = {
    **WEATHER_DESCRIPTORS,
    **WEATHER_PRECIPITATION,
    **WEATHER_OBSCURATION,
    **WEATHER_OTHER,
}


@dataclass(frozen=True, slots=True)
class WeatherPhenomenon:
    """Represents a weather phenomenon from a METAR observation.

    A weather phenomenon consists of:
    - Optional intensity qualifier (+, -, VC)
    - Optional descriptor (TS, SH, FZ, etc.)
    - One or more weather types (RA, SN, FG, etc.)

    Example: +TSRA = Heavy Thunderstorm with Rain
    """

    raw: str
    intensity: WeatherIntensity = WeatherIntensity.MODERATE
    descriptor: str | None = None
    phenomena: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        """Validate weather phenomenon data."""
        if not self.raw:
            raise ValueError("Raw weather string cannot be empty")

        if self.descriptor and self.descriptor not in WEATHER_DESCRIPTORS:
            raise ValueError(f"Unknown weather descriptor: {self.descriptor}")

        for code in self.phenomena:
            if code not in ALL_WEATHER_CODES:
                # Allow unknown codes but log warning
                pass

    @classmethod
    def from_code(cls, code: str) -> WeatherPhenomenon:
        """Parse a weather code string into a WeatherPhenomenon."""
        if not code:
            raise ValueError("Weather code cannot be empty")

        raw = code
        intensity = WeatherIntensity.MODERATE
        descriptor = None
        phenomena: list[str] = []

        # Parse intensity
        if code.startswith("-"):
            intensity = WeatherIntensity.LIGHT
            code = code[1:]
        elif code.startswith("+"):
            intensity = WeatherIntensity.HEAVY
            code = code[1:]
        elif code.startswith("VC"):
            intensity = WeatherIntensity.VICINITY
            code = code[2:]

        # Parse descriptor (always 2 characters if present)
        if len(code) >= 2 and code[:2] in WEATHER_DESCRIPTORS:
            descriptor = code[:2]
            code = code[2:]

        # Parse phenomena (2-character codes)
        while len(code) >= 2:
            phenomena.append(code[:2])
            code = code[2:]

        return cls(
            raw=raw,
            intensity=intensity,
            descriptor=descriptor,
            phenomena=tuple(phenomena),
        )

    @property
    def is_precipitation(self) -> bool:
        """Check if this phenomenon includes precipitation."""
        return any(p in WEATHER_PRECIPITATION for p in self.phenomena)

    @property
    def is_obscuration(self) -> bool:
        """Check if this phenomenon includes obscuration."""
        return any(p in WEATHER_OBSCURATION for p in self.phenomena)

    @property
    def is_thunderstorm(self) -> bool:
        """Check if this includes thunderstorm activity."""
        return self.descriptor == "TS"

    @property
    def is_freezing(self) -> bool:
        """Check if this includes freezing conditions."""
        return self.descriptor == "FZ"

    @property
    def description(self) -> str:
        """Return a human-readable description."""
        parts: list[str] = []

        if self.intensity != WeatherIntensity.MODERATE:
            parts.append(self.intensity.description)

        if self.descriptor:
            parts.append(WEATHER_DESCRIPTORS.get(self.descriptor, self.descriptor))

        for phenomenon in self.phenomena:
            parts.append(ALL_WEATHER_CODES.get(phenomenon, phenomenon))

        return " ".join(parts)

    def to_dict(self) -> dict[str, str | list[str] | None]:
        """Convert to dictionary for JSON serialization."""
        return {
            "raw": self.raw,
            "intensity": self.intensity.value if self.intensity.value else "moderate",
            "descriptor": self.descriptor,
            "phenomena": list(self.phenomena),
        }

    def __str__(self) -> str:
        """Return the raw code."""
        return self.raw
