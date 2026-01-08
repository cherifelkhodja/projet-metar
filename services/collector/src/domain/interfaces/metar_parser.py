"""METAR parser interface."""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from ..entities import MetarObservation


class MetarParseError(Exception):
    """Raised when METAR parsing fails."""

    def __init__(self, message: str, raw_metar: str):
        self.message = message
        self.raw_metar = raw_metar
        super().__init__(f"{message}: {raw_metar}")


class IMetarParser(ABC):
    """Interface for parsing raw METAR strings into structured data."""

    @abstractmethod
    def parse(self, raw_metar: str, source: str) -> MetarObservation:
        """Parse a raw METAR string into a MetarObservation.

        Args:
            raw_metar: The raw METAR string
            source: The source from which the METAR was fetched

        Returns:
            MetarObservation with all parsed fields

        Raises:
            MetarParseError: If parsing fails
        """
        ...

    @abstractmethod
    def validate(self, raw_metar: str) -> bool:
        """Validate if a string appears to be a valid METAR.

        Args:
            raw_metar: The raw METAR string to validate

        Returns:
            True if the string appears to be a valid METAR format
        """
        ...
