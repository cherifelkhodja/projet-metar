"""Use case for initializing airports from configuration."""

from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING, Any

import structlog
import yaml

from src.domain.entities import Airport

if TYPE_CHECKING:
    from src.domain.interfaces import IAirportRepository

logger = structlog.get_logger(__name__)


class InitializeAirportsUseCase:
    """Use case for loading initial airport configuration.

    Reads airports from a YAML configuration file and ensures
    they exist in the database.
    """

    def __init__(self, airport_repository: IAirportRepository):
        self._airport_repo = airport_repository

    async def execute(self, config_path: str | Path) -> int:
        """Load airports from configuration file.

        Args:
            config_path: Path to the airports.yaml file

        Returns:
            Number of airports added or updated
        """
        config_path = Path(config_path)

        if not config_path.exists():
            logger.warning("Airport config file not found", path=str(config_path))
            return 0

        try:
            with open(config_path) as f:
                config = yaml.safe_load(f)
        except yaml.YAMLError as e:
            logger.error("Failed to parse airport config", error=str(e))
            return 0

        airports_config = config.get("airports", [])
        if not airports_config:
            logger.warning("No airports in configuration")
            return 0

        count = 0
        for airport_data in airports_config:
            try:
                airport = self._create_airport(airport_data)
                await self._airport_repo.save(airport)
                count += 1
                logger.debug("Initialized airport", icao=airport.icao, name=airport.name)
            except Exception as e:
                logger.error(
                    "Failed to initialize airport",
                    data=airport_data,
                    error=str(e),
                )

        logger.info("Airports initialized", count=count)
        return count

    def _create_airport(self, data: dict[str, Any]) -> Airport:
        """Create an Airport entity from configuration data."""
        icao = data.get("icao")
        if not icao:
            raise ValueError("Airport configuration missing 'icao' field")

        return Airport.create(
            icao_code=icao,
            name=data.get("name"),
            latitude=data.get("latitude"),
            longitude=data.get("longitude"),
            elevation_ft=data.get("elevation_ft"),
            timezone=data.get("timezone"),
        )
