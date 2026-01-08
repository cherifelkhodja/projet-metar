"""Airport API routes."""

from __future__ import annotations

from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import delete, func, select
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.ext.asyncio import AsyncSession

from src.infrastructure.database import get_database
from src.infrastructure.models import AirportModel
from src.presentation.schemas import (
    AirportCreate,
    AirportListResponse,
    AirportResponse,
    MessageResponse,
)

router = APIRouter(prefix="/airports", tags=["Airports"])


async def get_session() -> AsyncSession:
    """Dependency to get database session."""
    db = get_database()
    async with db.session() as session:
        yield session


@router.get(
    "",
    response_model=AirportListResponse,
    summary="List all airports",
    description="Get list of all monitored airports",
)
async def list_airports(
    active_only: bool = True,
    session: AsyncSession = Depends(get_session),
) -> AirportListResponse:
    """List all airports."""
    query = select(AirportModel)
    if active_only:
        query = query.where(AirportModel.is_active == True)
    query = query.order_by(AirportModel.icao_code)

    result = await session.execute(query)
    models = result.scalars().all()

    airports = [AirportResponse.model_validate(m) for m in models]
    return AirportListResponse(airports=airports, total=len(airports))


@router.get(
    "/{icao}",
    response_model=AirportResponse,
    summary="Get airport details",
    description="Get details of a specific airport by ICAO code",
)
async def get_airport(
    icao: str,
    session: AsyncSession = Depends(get_session),
) -> AirportResponse:
    """Get airport by ICAO code."""
    icao = icao.upper()

    result = await session.execute(
        select(AirportModel).where(AirportModel.icao_code == icao)
    )
    model = result.scalar_one_or_none()

    if model is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Airport {icao} not found",
        )

    return AirportResponse.model_validate(model)


@router.post(
    "",
    response_model=AirportResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Add airport",
    description="Add a new airport to monitor",
)
async def create_airport(
    airport: AirportCreate,
    session: AsyncSession = Depends(get_session),
) -> AirportResponse:
    """Create a new airport."""
    now = datetime.utcnow()

    stmt = insert(AirportModel).values(
        icao_code=airport.icao_code,
        name=airport.name,
        latitude=airport.latitude,
        longitude=airport.longitude,
        elevation_ft=airport.elevation_ft,
        timezone=airport.timezone,
        is_active=True,
        created_at=now,
        updated_at=now,
    )
    stmt = stmt.on_conflict_do_update(
        index_elements=["icao_code"],
        set_={
            "name": stmt.excluded.name,
            "latitude": stmt.excluded.latitude,
            "longitude": stmt.excluded.longitude,
            "elevation_ft": stmt.excluded.elevation_ft,
            "timezone": stmt.excluded.timezone,
            "is_active": True,
            "updated_at": now,
        },
    )
    await session.execute(stmt)
    await session.commit()

    # Fetch the created/updated airport
    result = await session.execute(
        select(AirportModel).where(AirportModel.icao_code == airport.icao_code)
    )
    model = result.scalar_one()

    return AirportResponse.model_validate(model)


@router.delete(
    "/{icao}",
    response_model=MessageResponse,
    summary="Remove airport",
    description="Remove an airport from monitoring",
)
async def delete_airport(
    icao: str,
    session: AsyncSession = Depends(get_session),
) -> MessageResponse:
    """Delete an airport."""
    icao = icao.upper()

    result = await session.execute(
        delete(AirportModel).where(AirportModel.icao_code == icao)
    )

    if result.rowcount == 0:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Airport {icao} not found",
        )

    return MessageResponse(message=f"Airport {icao} deleted successfully")
