"""Cloud layer value object."""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum


class CloudCoverage(Enum):
    """Cloud coverage types in METAR reports."""

    SKC = "SKC"  # Sky Clear (manual observation)
    CLR = "CLR"  # Clear (automated, no clouds below 12,000ft)
    FEW = "FEW"  # Few (1/8 to 2/8 coverage)
    SCT = "SCT"  # Scattered (3/8 to 4/8 coverage)
    BKN = "BKN"  # Broken (5/8 to 7/8 coverage)
    OVC = "OVC"  # Overcast (8/8 coverage)
    VV = "VV"  # Vertical Visibility (obscured sky)
    NSC = "NSC"  # No Significant Cloud

    @property
    def description(self) -> str:
        """Return a human-readable description."""
        descriptions = {
            CloudCoverage.SKC: "Sky Clear",
            CloudCoverage.CLR: "Clear",
            CloudCoverage.FEW: "Few",
            CloudCoverage.SCT: "Scattered",
            CloudCoverage.BKN: "Broken",
            CloudCoverage.OVC: "Overcast",
            CloudCoverage.VV: "Vertical Visibility",
            CloudCoverage.NSC: "No Significant Cloud",
        }
        return descriptions.get(self, self.value)

    @property
    def is_ceiling(self) -> bool:
        """Check if this coverage type constitutes a ceiling."""
        return self in (CloudCoverage.BKN, CloudCoverage.OVC, CloudCoverage.VV)

    @classmethod
    def from_string(cls, value: str) -> CloudCoverage:
        """Create from string value."""
        try:
            return cls(value.upper())
        except ValueError:
            raise ValueError(f"Unknown cloud coverage type: {value}")


@dataclass(frozen=True, slots=True)
class CloudLayer:
    """Represents a single cloud layer in a METAR observation.

    Attributes:
        coverage: Type of cloud coverage (FEW, SCT, BKN, OVC, etc.)
        altitude_ft: Height of the cloud base in feet AGL
        cloud_type: Special cloud type (CB for Cumulonimbus, TCU for Towering Cumulus)
    """

    coverage: CloudCoverage
    altitude_ft: int | None = None
    cloud_type: str | None = None

    def __post_init__(self) -> None:
        """Validate cloud layer data."""
        if self.altitude_ft is not None and self.altitude_ft < 0:
            raise ValueError(f"Cloud altitude cannot be negative: {self.altitude_ft}")

        if self.cloud_type is not None and self.cloud_type not in ("CB", "TCU"):
            raise ValueError(f"Invalid cloud type: {self.cloud_type}. Must be CB or TCU.")

    @property
    def is_cumulonimbus(self) -> bool:
        """Check if this is a cumulonimbus cloud."""
        return self.cloud_type == "CB"

    @property
    def is_towering_cumulus(self) -> bool:
        """Check if this is a towering cumulus cloud."""
        return self.cloud_type == "TCU"

    @property
    def is_significant(self) -> bool:
        """Check if this cloud layer is significant for flight."""
        return self.coverage.is_ceiling or self.cloud_type is not None

    @property
    def altitude_m(self) -> int | None:
        """Return altitude in meters."""
        if self.altitude_ft is None:
            return None
        return int(self.altitude_ft * 0.3048)

    def to_dict(self) -> dict[str, str | int | None]:
        """Convert to dictionary for JSON serialization."""
        return {
            "coverage": self.coverage.value,
            "altitude_ft": self.altitude_ft,
            "cloud_type": self.cloud_type,
        }

    def __str__(self) -> str:
        """Return a human-readable representation."""
        parts = [self.coverage.description]
        if self.altitude_ft is not None:
            parts.append(f"at {self.altitude_ft}ft")
        if self.cloud_type:
            parts.append(f"({self.cloud_type})")
        return " ".join(parts)
