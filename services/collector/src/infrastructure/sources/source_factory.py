"""Factory for creating METAR sources."""

from __future__ import annotations

import structlog

from src.domain.interfaces import IMetarSource

from .checkwx_source import CheckWXSource
from .noaa_awc_source import NOAAAwcSource

logger = structlog.get_logger(__name__)


class MetarSourceFactory:
    """Factory for creating and managing METAR data sources.

    Supports:
    - Creating sources by name
    - Providing fallback sources
    - Managing source priorities
    """

    SOURCES = {
        "noaa_awc": NOAAAwcSource,
        "checkwx": CheckWXSource,
    }

    def __init__(
        self,
        noaa_base_url: str = "https://aviationweather.gov/api/data/metar",
        checkwx_api_key: str | None = None,
        checkwx_base_url: str = "https://api.checkwx.com/metar",
        timeout_seconds: float = 30.0,
        retry_attempts: int = 3,
        retry_delay_seconds: float = 5.0,
    ):
        self._config = {
            "noaa_base_url": noaa_base_url,
            "checkwx_api_key": checkwx_api_key,
            "checkwx_base_url": checkwx_base_url,
            "timeout_seconds": timeout_seconds,
            "retry_attempts": retry_attempts,
            "retry_delay_seconds": retry_delay_seconds,
        }
        self._sources: dict[str, IMetarSource] = {}

    def get_source(self, name: str) -> IMetarSource | None:
        """Get a source by name, creating it if necessary."""
        if name not in self.SOURCES:
            logger.warning("Unknown source requested", source=name)
            return None

        if name not in self._sources:
            self._sources[name] = self._create_source(name)

        return self._sources[name]

    def get_primary_source(self, primary_name: str = "noaa_awc") -> IMetarSource:
        """Get the primary source, with fallback if unavailable."""
        source = self.get_source(primary_name)
        if source and source.is_available:
            return source

        # Try other sources as fallback
        for name in self.SOURCES:
            if name != primary_name:
                source = self.get_source(name)
                if source and source.is_available:
                    logger.info(
                        "Using fallback source",
                        primary=primary_name,
                        fallback=name,
                    )
                    return source

        # If nothing else is available, return NOAA (always available)
        return self.get_source("noaa_awc") or self._create_source("noaa_awc")

    def get_available_sources(self) -> list[IMetarSource]:
        """Get all available sources."""
        available = []
        for name in self.SOURCES:
            source = self.get_source(name)
            if source and source.is_available:
                available.append(source)
        return available

    def _create_source(self, name: str) -> IMetarSource:
        """Create a new source instance."""
        common_kwargs = {
            "timeout_seconds": self._config["timeout_seconds"],
            "retry_attempts": self._config["retry_attempts"],
            "retry_delay_seconds": self._config["retry_delay_seconds"],
        }

        if name == "noaa_awc":
            return NOAAAwcSource(
                base_url=self._config["noaa_base_url"],
                **common_kwargs,
            )
        elif name == "checkwx":
            return CheckWXSource(
                api_key=self._config["checkwx_api_key"],
                base_url=self._config["checkwx_base_url"],
                **common_kwargs,
            )
        else:
            raise ValueError(f"Unknown source: {name}")

    async def close_all(self) -> None:
        """Close all source connections."""
        for source in self._sources.values():
            if hasattr(source, "close"):
                await source.close()  # type: ignore
        self._sources.clear()
