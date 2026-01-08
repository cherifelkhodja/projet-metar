"""Main entry point for the METAR API service."""

from __future__ import annotations

import logging
import sys
from contextlib import asynccontextmanager
from typing import AsyncGenerator

import structlog
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from src.config import Settings, get_settings
from src.infrastructure.database import init_database
from src.presentation.routes import (
    airports_router,
    collection_router,
    export_router,
    health_router,
    metar_router,
)
from src.presentation.routes.health import set_start_time


def setup_logging(level: str = "INFO", format: str = "json") -> None:
    """Configure structured logging."""
    log_level = getattr(logging, level.upper(), logging.INFO)

    logging.basicConfig(
        format="%(message)s",
        stream=sys.stdout,
        level=log_level,
    )

    logging.getLogger("uvicorn.access").setLevel(logging.WARNING)
    logging.getLogger("sqlalchemy.engine").setLevel(logging.WARNING)

    shared_processors: list[structlog.types.Processor] = [
        structlog.contextvars.merge_contextvars,
        structlog.stdlib.add_log_level,
        structlog.processors.TimeStamper(fmt="iso"),
        structlog.processors.UnicodeDecoder(),
    ]

    if format.lower() == "json":
        processors = shared_processors + [
            structlog.processors.format_exc_info,
            structlog.processors.JSONRenderer(),
        ]
    else:
        processors = shared_processors + [
            structlog.dev.ConsoleRenderer(colors=True),
        ]

    structlog.configure(
        processors=processors,
        wrapper_class=structlog.stdlib.BoundLogger,
        context_class=dict,
        logger_factory=structlog.stdlib.LoggerFactory(),
        cache_logger_on_first_use=True,
    )


def create_app(settings: Settings | None = None) -> FastAPI:
    """Create and configure the FastAPI application."""
    if settings is None:
        settings = get_settings()

    setup_logging(level=settings.log_level, format=settings.log_format)
    logger = structlog.get_logger(__name__)

    @asynccontextmanager
    async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
        """Application lifespan manager."""
        logger.info("Starting METAR API service")

        # Initialize database
        db = init_database(
            url=settings.database_url,
            echo=settings.log_level.upper() == "DEBUG",
        )
        await db.connect()

        # Set start time for metrics
        set_start_time()

        logger.info("METAR API service started")
        yield

        # Shutdown
        logger.info("Shutting down METAR API service")
        await db.disconnect()
        logger.info("METAR API service stopped")

    app = FastAPI(
        title="METAR Collector API",
        description="""
## METAR Data Collection API

This API provides access to collected METAR (Meteorological Aerodrome Report) data
for airports worldwide.

### Features

- **Airports**: Manage monitored airports
- **METAR**: Access current and historical METAR observations
- **Export**: Export data in CSV or JSON format
- **Health**: Monitor service health and metrics

### Data Sources

METAR data is collected from:
- NOAA Aviation Weather Center (primary)
- CheckWX API (backup)
        """,
        version="1.0.0",
        docs_url="/api/docs",
        redoc_url="/api/redoc",
        openapi_url="/api/openapi.json",
        lifespan=lifespan,
    )

    # CORS middleware
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # Exception handlers
    @app.exception_handler(Exception)
    async def global_exception_handler(request, exc):
        logger.error("Unhandled exception", error=str(exc), exc_info=True)
        return JSONResponse(
            status_code=500,
            content={"detail": "Internal server error"},
        )

    # Include routers
    app.include_router(health_router, prefix="/api/v1")
    app.include_router(airports_router, prefix="/api/v1")
    app.include_router(metar_router, prefix="/api/v1")
    app.include_router(collection_router, prefix="/api/v1")
    app.include_router(export_router, prefix="/api/v1")

    return app


# Create the application instance
app = create_app()


if __name__ == "__main__":
    import uvicorn

    settings = get_settings()
    uvicorn.run(
        "src.main:app",
        host=settings.api_host,
        port=settings.api_port,
        workers=settings.api_workers,
        reload=False,
    )
