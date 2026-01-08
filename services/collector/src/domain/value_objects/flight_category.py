"""Flight category value object."""

from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal
from enum import Enum
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from .cloud_layer import CloudLayer
    from .visibility import Visibility


class FlightCategoryType(Enum):
    """Flight category types based on FAA standards.

    VFR: Visual Flight Rules
    MVFR: Marginal VFR
    IFR: Instrument Flight Rules
    LIFR: Low IFR
    """

    VFR = "VFR"
    MVFR = "MVFR"
    IFR = "IFR"
    LIFR = "LIFR"

    @property
    def description(self) -> str:
        """Return human-readable description."""
        descriptions = {
            FlightCategoryType.VFR: "Visual Flight Rules",
            FlightCategoryType.MVFR: "Marginal VFR",
            FlightCategoryType.IFR: "Instrument Flight Rules",
            FlightCategoryType.LIFR: "Low IFR",
        }
        return descriptions[self]

    @property
    def color(self) -> str:
        """Return typical color coding for flight categories."""
        colors = {
            FlightCategoryType.VFR: "green",
            FlightCategoryType.MVFR: "blue",
            FlightCategoryType.IFR: "red",
            FlightCategoryType.LIFR: "magenta",
        }
        return colors[self]


@dataclass(frozen=True, slots=True)
class FlightCategory:
    """Represents the flight category calculated from METAR conditions.

    Flight categories are determined by:
    - Visibility (statute miles)
    - Ceiling (lowest BKN or OVC cloud layer)

    Thresholds (FAA):
    - LIFR: Visibility < 1 SM or Ceiling < 500 ft
    - IFR: Visibility 1-3 SM or Ceiling 500-1000 ft
    - MVFR: Visibility 3-5 SM or Ceiling 1000-3000 ft
    - VFR: Visibility > 5 SM and Ceiling > 3000 ft
    """

    category: FlightCategoryType
    visibility_category: FlightCategoryType
    ceiling_category: FlightCategoryType

    @classmethod
    def calculate(
        cls,
        visibility: Visibility | None,
        cloud_layers: list[CloudLayer],
    ) -> FlightCategory:
        """Calculate flight category from visibility and clouds.

        The worst (most restrictive) condition determines the overall category.
        """
        vis_cat = cls._visibility_category(visibility)
        ceil_cat = cls._ceiling_category(cloud_layers)

        # Return the most restrictive category
        categories = [FlightCategoryType.VFR, FlightCategoryType.MVFR,
                      FlightCategoryType.IFR, FlightCategoryType.LIFR]

        overall = max([vis_cat, ceil_cat], key=lambda c: categories.index(c))

        return cls(
            category=overall,
            visibility_category=vis_cat,
            ceiling_category=ceil_cat,
        )

    @staticmethod
    def _visibility_category(visibility: Visibility | None) -> FlightCategoryType:
        """Determine flight category based on visibility."""
        if visibility is None:
            return FlightCategoryType.VFR  # Assume VFR if no visibility reported

        if visibility.is_greater_than:
            return FlightCategoryType.VFR

        sm = visibility.statute_miles
        if sm is None:
            return FlightCategoryType.VFR

        if sm < Decimal("1"):
            return FlightCategoryType.LIFR
        if sm < Decimal("3"):
            return FlightCategoryType.IFR
        if sm <= Decimal("5"):
            return FlightCategoryType.MVFR
        return FlightCategoryType.VFR

    @staticmethod
    def _ceiling_category(cloud_layers: list[CloudLayer]) -> FlightCategoryType:
        """Determine flight category based on ceiling."""
        # Find the lowest ceiling (BKN, OVC, or VV)
        ceiling_ft: int | None = None

        for layer in cloud_layers:
            if layer.coverage.is_ceiling and layer.altitude_ft is not None:
                if ceiling_ft is None or layer.altitude_ft < ceiling_ft:
                    ceiling_ft = layer.altitude_ft

        if ceiling_ft is None:
            return FlightCategoryType.VFR  # No ceiling means clear skies

        if ceiling_ft < 500:
            return FlightCategoryType.LIFR
        if ceiling_ft < 1000:
            return FlightCategoryType.IFR
        if ceiling_ft <= 3000:
            return FlightCategoryType.MVFR
        return FlightCategoryType.VFR

    def __str__(self) -> str:
        """Return the category value."""
        return self.category.value
