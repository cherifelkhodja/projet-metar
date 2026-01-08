"""Repository interfaces for the METAR domain."""

from __future__ import annotations

from abc import ABC, abstractmethod
from datetime import datetime
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from ..entities import Airport, CollectionLog, MetarObservation
    from ..value_objects import ICAOCode


class IAirportRepository(ABC):
    """Interface for airport persistence operations."""

    @abstractmethod
    async def get_by_icao(self, icao_code: ICAOCode | str) -> Airport | None:
        """Retrieve an airport by its ICAO code."""
        ...

    @abstractmethod
    async def get_all(self, active_only: bool = True) -> list[Airport]:
        """Retrieve all airports, optionally filtering by active status."""
        ...

    @abstractmethod
    async def save(self, airport: Airport) -> Airport:
        """Save or update an airport."""
        ...

    @abstractmethod
    async def delete(self, icao_code: ICAOCode | str) -> bool:
        """Delete an airport by its ICAO code. Returns True if deleted."""
        ...

    @abstractmethod
    async def exists(self, icao_code: ICAOCode | str) -> bool:
        """Check if an airport exists."""
        ...

    @abstractmethod
    async def count(self, active_only: bool = True) -> int:
        """Count airports, optionally filtering by active status."""
        ...


class IMetarObservationRepository(ABC):
    """Interface for METAR observation persistence operations."""

    @abstractmethod
    async def save(self, observation: MetarObservation) -> MetarObservation:
        """Save a METAR observation. Returns the saved observation with ID."""
        ...

    @abstractmethod
    async def save_batch(self, observations: list[MetarObservation]) -> int:
        """Save multiple observations. Returns count of saved observations."""
        ...

    @abstractmethod
    async def get_latest(self, icao_code: ICAOCode | str) -> MetarObservation | None:
        """Get the latest METAR observation for an airport."""
        ...

    @abstractmethod
    async def get_latest_bulk(
        self, icao_codes: list[ICAOCode | str] | None = None
    ) -> list[MetarObservation]:
        """Get the latest METAR for multiple airports (or all if no codes specified)."""
        ...

    @abstractmethod
    async def get_history(
        self,
        icao_code: ICAOCode | str,
        start_date: datetime | None = None,
        end_date: datetime | None = None,
        page: int = 1,
        per_page: int = 50,
    ) -> tuple[list[MetarObservation], int]:
        """Get historical observations with pagination. Returns (observations, total_count)."""
        ...

    @abstractmethod
    async def exists(self, icao_code: ICAOCode | str, observation_time: datetime) -> bool:
        """Check if an observation already exists (for deduplication)."""
        ...

    @abstractmethod
    async def count(
        self,
        icao_code: ICAOCode | str | None = None,
        start_date: datetime | None = None,
        end_date: datetime | None = None,
    ) -> int:
        """Count observations with optional filters."""
        ...

    @abstractmethod
    async def delete_before(self, cutoff_date: datetime) -> int:
        """Delete observations before a date. Returns count of deleted records."""
        ...


class ICollectionLogRepository(ABC):
    """Interface for collection log persistence operations."""

    @abstractmethod
    async def save(self, log: CollectionLog) -> CollectionLog:
        """Save or update a collection log. Returns the saved log with ID."""
        ...

    @abstractmethod
    async def get_latest(self) -> CollectionLog | None:
        """Get the most recent collection log."""
        ...

    @abstractmethod
    async def get_running(self) -> CollectionLog | None:
        """Get currently running collection, if any."""
        ...

    @abstractmethod
    async def get_history(
        self,
        page: int = 1,
        per_page: int = 20,
    ) -> tuple[list[CollectionLog], int]:
        """Get collection history with pagination. Returns (logs, total_count)."""
        ...

    @abstractmethod
    async def get_statistics(
        self,
        start_date: datetime | None = None,
        end_date: datetime | None = None,
    ) -> dict[str, int | float]:
        """Get aggregate statistics for collection runs."""
        ...
