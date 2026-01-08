"""Collection log entity."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Self


class CollectionStatus(Enum):
    """Status of a collection run."""

    RUNNING = "running"
    SUCCESS = "success"
    PARTIAL = "partial"  # Some airports failed
    FAILED = "failed"

    @property
    def is_terminal(self) -> bool:
        """Check if this is a terminal (final) status."""
        return self in (CollectionStatus.SUCCESS, CollectionStatus.PARTIAL, CollectionStatus.FAILED)


@dataclass
class CollectionLog:
    """Represents a log entry for a METAR collection run.

    Tracks the execution and results of scheduled collection jobs.
    """

    started_at: datetime
    status: CollectionStatus = CollectionStatus.RUNNING
    completed_at: datetime | None = None

    # Counts
    airports_requested: int = 0
    airports_success: int = 0
    airports_failed: int = 0
    new_observations: int = 0
    duplicates_skipped: int = 0

    # Error information
    error_message: str | None = None
    details: dict[str, Any] = field(default_factory=dict)

    # Database ID
    id: int | None = None

    @classmethod
    def start(cls, airports_count: int) -> Self:
        """Create a new collection log entry at the start of a run."""
        return cls(
            started_at=datetime.utcnow(),
            status=CollectionStatus.RUNNING,
            airports_requested=airports_count,
        )

    def record_success(self, icao: str) -> None:
        """Record a successful collection for an airport."""
        self.airports_success += 1
        if "successful_airports" not in self.details:
            self.details["successful_airports"] = []
        self.details["successful_airports"].append(icao)

    def record_failure(self, icao: str, error: str) -> None:
        """Record a failed collection for an airport."""
        self.airports_failed += 1
        if "failed_airports" not in self.details:
            self.details["failed_airports"] = {}
        self.details["failed_airports"][icao] = error

    def record_new_observation(self) -> None:
        """Increment the count of new observations."""
        self.new_observations += 1

    def record_duplicate(self) -> None:
        """Increment the count of skipped duplicates."""
        self.duplicates_skipped += 1

    def complete(self, error_message: str | None = None) -> None:
        """Mark the collection run as complete."""
        self.completed_at = datetime.utcnow()

        if error_message:
            self.status = CollectionStatus.FAILED
            self.error_message = error_message
        elif self.airports_failed == 0:
            self.status = CollectionStatus.SUCCESS
        elif self.airports_success > 0:
            self.status = CollectionStatus.PARTIAL
        else:
            self.status = CollectionStatus.FAILED

    @property
    def duration_seconds(self) -> float | None:
        """Return the duration of the collection run in seconds."""
        if self.completed_at is None:
            return None
        delta = self.completed_at - self.started_at
        return delta.total_seconds()

    @property
    def success_rate(self) -> float:
        """Return the success rate as a percentage."""
        if self.airports_requested == 0:
            return 0.0
        return (self.airports_success / self.airports_requested) * 100

    @property
    def is_running(self) -> bool:
        """Check if the collection is still running."""
        return self.status == CollectionStatus.RUNNING

    @property
    def is_complete(self) -> bool:
        """Check if the collection is complete."""
        return self.status.is_terminal

    def __str__(self) -> str:
        """Return string representation."""
        status = self.status.value
        if self.is_complete:
            return (
                f"Collection [{status}]: {self.airports_success}/{self.airports_requested} "
                f"airports, {self.new_observations} new observations"
            )
        return f"Collection [{status}]: {self.airports_requested} airports requested"
