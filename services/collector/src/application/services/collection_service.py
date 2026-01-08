"""Collection service for orchestrating METAR data collection."""

from __future__ import annotations

from typing import TYPE_CHECKING

import structlog

from src.domain.entities import CollectionLog
from src.domain.interfaces import MetarParseError

if TYPE_CHECKING:
    from src.domain.interfaces import (
        IAirportRepository,
        ICollectionLogRepository,
        IMetarObservationRepository,
        IMetarParser,
        IMetarSource,
    )

logger = structlog.get_logger(__name__)


class CollectionService:
    """Service for collecting METAR data from external sources.

    Orchestrates the collection process:
    1. Fetch list of active airports
    2. Request METAR data from source
    3. Parse raw METAR strings
    4. Store observations in database
    5. Log collection results
    """

    def __init__(
        self,
        airport_repository: IAirportRepository,
        observation_repository: IMetarObservationRepository,
        collection_log_repository: ICollectionLogRepository,
        metar_source: IMetarSource,
        metar_parser: IMetarParser,
    ):
        self._airport_repo = airport_repository
        self._observation_repo = observation_repository
        self._log_repo = collection_log_repository
        self._source = metar_source
        self._parser = metar_parser

    async def collect_all(self) -> CollectionLog:
        """Collect METAR data for all active airports.

        Returns:
            CollectionLog with results of the collection run
        """
        # Get active airports
        airports = await self._airport_repo.get_all(active_only=True)
        icao_codes = [airport.icao for airport in airports]

        if not icao_codes:
            logger.warning("No active airports to collect")
            log = CollectionLog.start(0)
            log.complete()
            await self._log_repo.save(log)
            return log

        logger.info(
            "Starting METAR collection",
            airport_count=len(icao_codes),
            source=self._source.name,
        )

        # Start collection log
        log = CollectionLog.start(len(icao_codes))
        await self._log_repo.save(log)

        try:
            # Fetch METARs from source
            results = await self._source.fetch_metars(icao_codes)

            # Process results
            for result in results:
                if result.success and result.raw_metar:
                    await self._process_metar(result.icao_code, result.raw_metar, log)
                else:
                    log.record_failure(result.icao_code, result.error_message or "Unknown error")
                    logger.warning(
                        "Failed to fetch METAR",
                        icao=result.icao_code,
                        error=result.error_message,
                    )

            log.complete()

        except Exception as e:
            logger.error("Collection failed with exception", error=str(e))
            log.complete(error_message=str(e))

        # Save final log
        await self._log_repo.save(log)

        logger.info(
            "Collection completed",
            status=log.status.value,
            success=log.airports_success,
            failed=log.airports_failed,
            new_observations=log.new_observations,
            duplicates=log.duplicates_skipped,
        )

        return log

    async def collect_airport(self, icao_code: str) -> CollectionLog:
        """Collect METAR for a single airport.

        Args:
            icao_code: ICAO code of the airport

        Returns:
            CollectionLog with results
        """
        logger.info("Collecting METAR for airport", icao=icao_code, source=self._source.name)

        log = CollectionLog.start(1)
        await self._log_repo.save(log)

        try:
            result = await self._source.fetch_metar(icao_code)

            if result.success and result.raw_metar:
                await self._process_metar(result.icao_code, result.raw_metar, log)
            else:
                log.record_failure(result.icao_code, result.error_message or "Unknown error")

            log.complete()

        except Exception as e:
            logger.error("Collection failed", icao=icao_code, error=str(e))
            log.complete(error_message=str(e))

        await self._log_repo.save(log)
        return log

    async def _process_metar(
        self,
        icao_code: str,
        raw_metar: str,
        log: CollectionLog,
    ) -> None:
        """Process and store a raw METAR string."""
        try:
            # Parse the METAR
            observation = self._parser.parse(raw_metar, self._source.name)

            # Check for duplicate
            exists = await self._observation_repo.exists(
                observation.icao_code,
                observation.observation_time,
            )

            if exists:
                log.record_duplicate()
                logger.debug("Skipping duplicate METAR", icao=icao_code)
            else:
                # Save the observation
                await self._observation_repo.save(observation)
                log.record_new_observation()
                logger.debug(
                    "Saved new METAR",
                    icao=icao_code,
                    time=observation.observation_time.isoformat(),
                )

            log.record_success(icao_code)

        except MetarParseError as e:
            log.record_failure(icao_code, f"Parse error: {e.message}")
            logger.warning("Failed to parse METAR", icao=icao_code, error=str(e))

        except Exception as e:
            log.record_failure(icao_code, str(e))
            logger.error("Failed to process METAR", icao=icao_code, error=str(e))
