"""Domain interfaces (ports) for the METAR domain."""

from .metar_parser import IMetarParser
from .metar_source import IMetarSource, MetarSourceError, MetarSourceResult
from .repositories import (
    IAirportRepository,
    ICollectionLogRepository,
    IMetarObservationRepository,
)

__all__ = [
    "IAirportRepository",
    "IMetarObservationRepository",
    "ICollectionLogRepository",
    "IMetarSource",
    "MetarSourceResult",
    "MetarSourceError",
    "IMetarParser",
]
