"""Health and metrics API routes."""

from __future__ import annotations

from datetime import datetime

from fastapi import APIRouter, Depends
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from src.infrastructure.database import get_database
from src.infrastructure.models import (
    AirportModel,
    CollectionLogModel,
    MetarObservationModel,
)
from src.presentation.schemas import MetricsResponse

router = APIRouter(tags=["Health"])

# Track service start time
_start_time: datetime | None = None


def set_start_time() -> None:
    """Set the service start time."""
    global _start_time
    _start_time = datetime.utcnow()


async def get_session() -> AsyncSession:
    """Dependency to get database session."""
    db = get_database()
    async with db.session() as session:
        yield session


@router.get(
    "/health",
    summary="Health check",
    description="Check if the API service is healthy",
)
async def health_check() -> dict:
    """Health check endpoint."""
    try:
        db = get_database()
        async with db.session() as session:
            await session.execute(select(1))
        db_status = "healthy"
    except Exception as e:
        db_status = f"unhealthy: {e}"

    return {
        "status": "healthy" if db_status == "healthy" else "degraded",
        "database": db_status,
        "timestamp": datetime.utcnow().isoformat(),
    }


@router.get(
    "/metrics",
    response_model=MetricsResponse,
    summary="Get metrics",
    description="Get service metrics and statistics",
)
async def get_metrics(
    session: AsyncSession = Depends(get_session),
) -> MetricsResponse:
    """Get service metrics."""
    # Airport counts
    total_airports = (
        await session.execute(select(func.count()).select_from(AirportModel))
    ).scalar_one()

    active_airports = (
        await session.execute(
            select(func.count())
            .select_from(AirportModel)
            .where(AirportModel.is_active == True)
        )
    ).scalar_one()

    # Observation counts
    total_observations = (
        await session.execute(select(func.count()).select_from(MetarObservationModel))
    ).scalar_one()

    # Observation time range
    oldest_obs = (
        await session.execute(
            select(func.min(MetarObservationModel.observation_time))
        )
    ).scalar_one()

    newest_obs = (
        await session.execute(
            select(func.max(MetarObservationModel.observation_time))
        )
    ).scalar_one()

    # Collection stats
    collection_stats = await session.execute(
        select(
            func.count().label("total"),
            func.sum(
                func.cast(CollectionLogModel.status == "success", Integer)
            ).label("successful"),
            func.sum(
                func.cast(CollectionLogModel.status == "failed", Integer)
            ).label("failed"),
            func.avg(CollectionLogModel.new_observations).label("avg_obs"),
        ).select_from(CollectionLogModel)
    )
    stats = collection_stats.one()

    # Calculate uptime
    uptime = None
    if _start_time:
        uptime = (datetime.utcnow() - _start_time).total_seconds()

    return MetricsResponse(
        total_airports=total_airports,
        active_airports=active_airports,
        total_observations=total_observations,
        total_collections=stats.total or 0,
        successful_collections=int(stats.successful or 0),
        failed_collections=int(stats.failed or 0),
        avg_observations_per_run=float(stats.avg_obs or 0),
        oldest_observation=oldest_obs,
        newest_observation=newest_obs,
        uptime_seconds=uptime,
    )


# Import Integer for casting
from sqlalchemy import Integer
