"""METAR API routes."""

from __future__ import annotations

from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from src.infrastructure.database import get_database
from src.infrastructure.models import MetarObservationModel
from src.presentation.schemas import (
    MetarBulkResponse,
    MetarHistoryResponse,
    MetarResponse,
)

router = APIRouter(prefix="/metar", tags=["METAR"])


async def get_session() -> AsyncSession:
    """Dependency to get database session."""
    db = get_database()
    async with db.session() as session:
        yield session


@router.get(
    "/{icao}/latest",
    response_model=MetarResponse,
    summary="Get latest METAR",
    description="Get the most recent METAR observation for an airport",
)
async def get_latest_metar(
    icao: str,
    session: AsyncSession = Depends(get_session),
) -> MetarResponse:
    """Get latest METAR for an airport."""
    icao = icao.upper()

    result = await session.execute(
        select(MetarObservationModel)
        .where(MetarObservationModel.icao_code == icao)
        .order_by(MetarObservationModel.observation_time.desc())
        .limit(1)
    )
    model = result.scalar_one_or_none()

    if model is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"No METAR found for {icao}",
        )

    return MetarResponse.from_model(model)


@router.get(
    "/{icao}/history",
    response_model=MetarHistoryResponse,
    summary="Get METAR history",
    description="Get historical METAR observations for an airport",
)
async def get_metar_history(
    icao: str,
    start_date: datetime | None = Query(None, description="Start date filter"),
    end_date: datetime | None = Query(None, description="End date filter"),
    page: int = Query(1, ge=1, description="Page number"),
    per_page: int = Query(50, ge=1, le=100, description="Items per page"),
    session: AsyncSession = Depends(get_session),
) -> MetarHistoryResponse:
    """Get METAR history for an airport."""
    icao = icao.upper()
    offset = (page - 1) * per_page

    # Base query
    base_query = select(MetarObservationModel).where(
        MetarObservationModel.icao_code == icao
    )

    if start_date:
        base_query = base_query.where(
            MetarObservationModel.observation_time >= start_date
        )
    if end_date:
        base_query = base_query.where(
            MetarObservationModel.observation_time <= end_date
        )

    # Count query
    count_query = select(func.count()).select_from(base_query.subquery())
    total = (await session.execute(count_query)).scalar_one()

    # Data query
    data_query = (
        base_query.order_by(MetarObservationModel.observation_time.desc())
        .offset(offset)
        .limit(per_page)
    )

    result = await session.execute(data_query)
    models = result.scalars().all()

    observations = [MetarResponse.from_model(m) for m in models]
    pages = (total + per_page - 1) // per_page if per_page > 0 else 0

    return MetarHistoryResponse(
        icao_code=icao,
        observations=observations,
        total=total,
        page=page,
        per_page=per_page,
        pages=pages,
    )


@router.get(
    "/bulk/latest",
    response_model=MetarBulkResponse,
    summary="Get latest METARs",
    description="Get the latest METAR for all monitored airports",
)
async def get_bulk_latest(
    session: AsyncSession = Depends(get_session),
) -> MetarBulkResponse:
    """Get latest METARs for all airports."""
    # Subquery to get latest observation time per airport
    subquery = (
        select(
            MetarObservationModel.icao_code,
            func.max(MetarObservationModel.observation_time).label("max_time"),
        )
        .group_by(MetarObservationModel.icao_code)
        .subquery()
    )

    # Main query
    query = (
        select(MetarObservationModel)
        .join(
            subquery,
            (MetarObservationModel.icao_code == subquery.c.icao_code)
            & (MetarObservationModel.observation_time == subquery.c.max_time),
        )
        .order_by(MetarObservationModel.icao_code)
    )

    result = await session.execute(query)
    models = result.scalars().all()

    observations = [MetarResponse.from_model(m) for m in models]

    return MetarBulkResponse(observations=observations, count=len(observations))
