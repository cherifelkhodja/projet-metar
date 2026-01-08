"""METAR source interface for fetching raw METAR data."""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from ..value_objects import ICAOCode


class MetarSourceError(Exception):
    """Base exception for METAR source errors."""

    def __init__(self, message: str, source: str, icao_code: str | None = None):
        self.message = message
        self.source = source
        self.icao_code = icao_code
        super().__init__(message)


class MetarSourceConnectionError(MetarSourceError):
    """Raised when connection to the source fails."""

    pass


class MetarSourceTimeoutError(MetarSourceError):
    """Raised when the source request times out."""

    pass


class MetarSourceRateLimitError(MetarSourceError):
    """Raised when rate limit is exceeded."""

    pass


@dataclass
class MetarSourceResult:
    """Result from fetching METAR data from a source."""

    icao_code: str
    raw_metar: str | None
    success: bool
    error_message: str | None = None

    @classmethod
    def success_result(cls, icao_code: str, raw_metar: str) -> MetarSourceResult:
        """Create a successful result."""
        return cls(icao_code=icao_code, raw_metar=raw_metar, success=True)

    @classmethod
    def failure_result(cls, icao_code: str, error_message: str) -> MetarSourceResult:
        """Create a failure result."""
        return cls(
            icao_code=icao_code,
            raw_metar=None,
            success=False,
            error_message=error_message,
        )


class IMetarSource(ABC):
    """Interface for METAR data sources.

    Implementations should handle:
    - Network connectivity issues
    - Rate limiting
    - Response parsing
    - Error handling
    """

    @property
    @abstractmethod
    def name(self) -> str:
        """Return the name of this source."""
        ...

    @property
    @abstractmethod
    def is_available(self) -> bool:
        """Check if the source is currently available (e.g., API key configured)."""
        ...

    @abstractmethod
    async def fetch_metar(self, icao_code: ICAOCode | str) -> MetarSourceResult:
        """Fetch METAR for a single airport.

        Args:
            icao_code: The ICAO code of the airport

        Returns:
            MetarSourceResult with the raw METAR string or error information
        """
        ...

    @abstractmethod
    async def fetch_metars(
        self, icao_codes: list[ICAOCode | str]
    ) -> list[MetarSourceResult]:
        """Fetch METARs for multiple airports.

        Some sources support batch requests, which is more efficient.

        Args:
            icao_codes: List of ICAO codes

        Returns:
            List of MetarSourceResult, one per airport
        """
        ...

    @abstractmethod
    async def health_check(self) -> bool:
        """Check if the source is healthy and responding."""
        ...
