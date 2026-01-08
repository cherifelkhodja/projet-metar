"""Main entry point for the METAR Collector service."""

from __future__ import annotations

import asyncio
import signal
from datetime import datetime

import structlog
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.interval import IntervalTrigger

from src.application.services import CollectionService
from src.application.use_cases import InitializeAirportsUseCase
from src.config import Settings, get_settings
from src.infrastructure.parsers import MetarParser
from src.infrastructure.persistence import (
    Database,
    SQLAlchemyAirportRepository,
    SQLAlchemyCollectionLogRepository,
    SQLAlchemyMetarObservationRepository,
)
from src.infrastructure.persistence.database import init_database
from src.infrastructure.sources import MetarSourceFactory
from src.logging_config import setup_logging

logger = structlog.get_logger(__name__)


class CollectorApp:
    """Main application class for the METAR Collector service."""

    def __init__(self, settings: Settings):
        self.settings = settings
        self.database: Database | None = None
        self.scheduler: AsyncIOScheduler | None = None
        self.source_factory: MetarSourceFactory | None = None
        self.collection_service: CollectionService | None = None
        self._shutdown_event = asyncio.Event()

    async def initialize(self) -> None:
        """Initialize all components."""
        logger.info("Initializing METAR Collector service")

        # Initialize database
        self.database = init_database(
            url=self.settings.database_url,
            echo=self.settings.log_level.upper() == "DEBUG",
        )
        await self.database.connect()

        # Initialize repositories
        airport_repo = SQLAlchemyAirportRepository(self.database)
        observation_repo = SQLAlchemyMetarObservationRepository(self.database)
        log_repo = SQLAlchemyCollectionLogRepository(self.database)

        # Initialize source factory
        self.source_factory = MetarSourceFactory(
            noaa_base_url=self.settings.noaa_awc_base_url,
            checkwx_api_key=self.settings.checkwx_api_key,
            checkwx_base_url=self.settings.checkwx_base_url,
            timeout_seconds=self.settings.collection_timeout_seconds,
            retry_attempts=self.settings.collection_retry_attempts,
            retry_delay_seconds=self.settings.collection_retry_delay_seconds,
        )

        # Get primary source
        source = self.source_factory.get_primary_source(self.settings.primary_source)

        # Initialize parser
        parser = MetarParser()

        # Initialize collection service
        self.collection_service = CollectionService(
            airport_repository=airport_repo,
            observation_repository=observation_repo,
            collection_log_repository=log_repo,
            metar_source=source,
            metar_parser=parser,
        )

        # Initialize airports from config
        init_use_case = InitializeAirportsUseCase(airport_repo)
        await init_use_case.execute(self.settings.airports_config_path)

        # Initialize scheduler
        self.scheduler = AsyncIOScheduler()

        logger.info("METAR Collector service initialized")

    async def start(self) -> None:
        """Start the collector service."""
        if self.scheduler is None or self.collection_service is None:
            raise RuntimeError("Service not initialized. Call initialize() first.")

        logger.info(
            "Starting METAR collection scheduler",
            interval_minutes=self.settings.collection_interval_minutes,
        )

        # Schedule collection job
        self.scheduler.add_job(
            self._run_collection,
            trigger=IntervalTrigger(minutes=self.settings.collection_interval_minutes),
            id="metar_collection",
            name="METAR Collection Job",
            next_run_time=datetime.now(),  # Run immediately on start
            replace_existing=True,
        )

        self.scheduler.start()

        # Wait for shutdown signal
        await self._shutdown_event.wait()

    async def stop(self) -> None:
        """Stop the collector service gracefully."""
        logger.info("Stopping METAR Collector service")

        if self.scheduler:
            self.scheduler.shutdown(wait=True)

        if self.source_factory:
            await self.source_factory.close_all()

        if self.database:
            await self.database.disconnect()

        logger.info("METAR Collector service stopped")

    def request_shutdown(self) -> None:
        """Request graceful shutdown."""
        self._shutdown_event.set()

    async def _run_collection(self) -> None:
        """Execute a collection run."""
        if self.collection_service is None:
            return

        try:
            logger.info("Starting scheduled collection")
            log = await self.collection_service.collect_all()
            logger.info(
                "Scheduled collection completed",
                status=log.status.value,
                new_observations=log.new_observations,
            )
        except Exception as e:
            logger.error("Collection run failed", error=str(e), exc_info=True)


async def main() -> None:
    """Main entry point."""
    settings = get_settings()
    setup_logging(level=settings.log_level, format=settings.log_format)

    app = CollectorApp(settings)

    # Set up signal handlers
    loop = asyncio.get_running_loop()

    def signal_handler() -> None:
        logger.info("Received shutdown signal")
        app.request_shutdown()

    for sig in (signal.SIGTERM, signal.SIGINT):
        loop.add_signal_handler(sig, signal_handler)

    try:
        await app.initialize()
        await app.start()
    except Exception as e:
        logger.error("Application error", error=str(e), exc_info=True)
        raise
    finally:
        await app.stop()


if __name__ == "__main__":
    asyncio.run(main())
