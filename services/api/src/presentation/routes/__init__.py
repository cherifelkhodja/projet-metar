"""API routes."""

from .airports import router as airports_router
from .collection import router as collection_router
from .export import router as export_router
from .health import router as health_router
from .metar import router as metar_router

__all__ = [
    "airports_router",
    "metar_router",
    "collection_router",
    "export_router",
    "health_router",
]
