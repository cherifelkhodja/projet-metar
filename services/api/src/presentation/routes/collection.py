"""Collection status API routes."""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.infrastructure.database import get_database
from src.infrastructure.models import CollectionLogModel
from src.presentation.schemas import (
    CollectionLogResponse,
    CollectionStatusResponse,
    MessageResponse,
)

router = APIRouter(prefix="/collection", tags=["Collection"])


async def get_session() -> AsyncSession:
    """Dependency to get database session."""
    db = get_database()
    async with db.session() as session:
        yield session


@router.get(
    "/status",
    response_model=CollectionStatusResponse,
    summary="Get collection status",
    description="Get the current status of METAR collection",
)
async def get_collection_status(
    session: AsyncSession = Depends(get_session),
) -> CollectionStatusResponse:
    """Get current collection status."""
    # Get latest collection log
    result = await session.execute(
        select(CollectionLogModel)
        .order_by(CollectionLogModel.started_at.desc())
        .limit(1)
    )
    latest = result.scalar_one_or_none()

    # Check if any collection is running
    running_result = await session.execute(
        select(CollectionLogModel)
        .where(CollectionLogModel.status == "running")
        .limit(1)
    )
    is_running = running_result.scalar_one_or_none() is not None

    last_collection = None
    if latest:
        last_collection = CollectionLogResponse.model_validate(latest)

    return CollectionStatusResponse(
        last_collection=last_collection,
        is_running=is_running,
        next_scheduled=None,  # Would need to query scheduler
    )


@router.get(
    "/history",
    response_model=list[CollectionLogResponse],
    summary="Get collection history",
    description="Get history of collection runs",
)
async def get_collection_history(
    page: int = 1,
    per_page: int = 20,
    session: AsyncSession = Depends(get_session),
) -> list[CollectionLogResponse]:
    """Get collection history."""
    offset = (page - 1) * per_page

    result = await session.execute(
        select(CollectionLogModel)
        .order_by(CollectionLogModel.started_at.desc())
        .offset(offset)
        .limit(per_page)
    )
    models = result.scalars().all()

    return [CollectionLogResponse.model_validate(m) for m in models]


@router.post(
    "/trigger",
    response_model=MessageResponse,
    summary="Trigger collection",
    description="Manually trigger a METAR collection run",
)
async def trigger_collection() -> MessageResponse:
    """Trigger manual collection.

    Note: This endpoint is a placeholder. In a full implementation,
    this would communicate with the collector service to trigger
    an immediate collection run.
    """
    # In a production system, this would:
    # 1. Send a message to the collector service (via message queue, HTTP, etc.)
    # 2. Return immediately with acknowledgment
    # 3. Collection would run asynchronously

    return MessageResponse(
        message="Collection triggered. Check status endpoint for results.",
        success=True,
    )
