"""Export API routes."""

from __future__ import annotations

import csv
import io
from datetime import datetime

from fastapi import APIRouter, Depends, Query
from fastapi.responses import StreamingResponse
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.infrastructure.database import get_database
from src.infrastructure.models import MetarObservationModel
from src.presentation.schemas import MetarResponse

router = APIRouter(prefix="/export", tags=["Export"])


async def get_session() -> AsyncSession:
    """Dependency to get database session."""
    db = get_database()
    async with db.session() as session:
        yield session


@router.get(
    "/csv",
    summary="Export to CSV",
    description="Export METAR data in CSV format",
    response_class=StreamingResponse,
)
async def export_csv(
    icao: str | None = Query(None, description="Filter by ICAO code"),
    start_date: datetime | None = Query(None, description="Start date"),
    end_date: datetime | None = Query(None, description="End date"),
    session: AsyncSession = Depends(get_session),
) -> StreamingResponse:
    """Export METAR data as CSV."""
    query = select(MetarObservationModel)

    if icao:
        query = query.where(MetarObservationModel.icao_code == icao.upper())
    if start_date:
        query = query.where(MetarObservationModel.observation_time >= start_date)
    if end_date:
        query = query.where(MetarObservationModel.observation_time <= end_date)

    query = query.order_by(
        MetarObservationModel.icao_code,
        MetarObservationModel.observation_time.desc(),
    )

    result = await session.execute(query)
    models = result.scalars().all()

    # Create CSV in memory
    output = io.StringIO()
    writer = csv.writer(output)

    # Header
    writer.writerow([
        "icao_code",
        "observation_time",
        "raw_metar",
        "wind_direction",
        "wind_speed_kt",
        "wind_gust_kt",
        "visibility_sm",
        "visibility_m",
        "ceiling_ft",
        "temperature_c",
        "dewpoint_c",
        "altimeter_inhg",
        "altimeter_hpa",
        "flight_category",
        "source",
        "fetched_at",
    ])

    # Data rows
    for model in models:
        writer.writerow([
            model.icao_code,
            model.observation_time.isoformat() if model.observation_time else "",
            model.raw_metar,
            model.wind_direction_degrees or "",
            model.wind_speed_kt or "",
            model.wind_gust_kt or "",
            str(model.visibility_statute_mi) if model.visibility_statute_mi else "",
            model.visibility_meters or "",
            model.ceiling_ft or "",
            str(model.temperature_c) if model.temperature_c else "",
            str(model.dewpoint_c) if model.dewpoint_c else "",
            str(model.altimeter_inhg) if model.altimeter_inhg else "",
            model.altimeter_hpa or "",
            model.flight_category or "",
            model.source,
            model.fetched_at.isoformat() if model.fetched_at else "",
        ])

    output.seek(0)

    # Generate filename
    filename = "metar_export"
    if icao:
        filename += f"_{icao}"
    filename += f"_{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}.csv"

    return StreamingResponse(
        iter([output.getvalue()]),
        media_type="text/csv",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


@router.get(
    "/json",
    summary="Export to JSON",
    description="Export METAR data in JSON format",
)
async def export_json(
    icao: str | None = Query(None, description="Filter by ICAO code"),
    start_date: datetime | None = Query(None, description="Start date"),
    end_date: datetime | None = Query(None, description="End date"),
    session: AsyncSession = Depends(get_session),
) -> dict:
    """Export METAR data as JSON."""
    query = select(MetarObservationModel)

    if icao:
        query = query.where(MetarObservationModel.icao_code == icao.upper())
    if start_date:
        query = query.where(MetarObservationModel.observation_time >= start_date)
    if end_date:
        query = query.where(MetarObservationModel.observation_time <= end_date)

    query = query.order_by(
        MetarObservationModel.icao_code,
        MetarObservationModel.observation_time.desc(),
    )

    result = await session.execute(query)
    models = result.scalars().all()

    observations = [MetarResponse.from_model(m) for m in models]

    return {
        "count": len(observations),
        "exported_at": datetime.utcnow().isoformat(),
        "filters": {
            "icao": icao,
            "start_date": start_date.isoformat() if start_date else None,
            "end_date": end_date.isoformat() if end_date else None,
        },
        "observations": [o.model_dump() for o in observations],
    }
