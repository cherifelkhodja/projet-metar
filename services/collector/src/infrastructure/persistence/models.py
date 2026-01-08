"""SQLAlchemy ORM models."""

from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from typing import Any

from sqlalchemy import (
    BigInteger,
    Boolean,
    DateTime,
    Index,
    Integer,
    Numeric,
    String,
    Text,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


class Base(DeclarativeBase):
    """Base class for all ORM models."""

    pass


class AirportModel(Base):
    """ORM model for airports table."""

    __tablename__ = "airports"

    icao_code: Mapped[str] = mapped_column(String(4), primary_key=True)
    name: Mapped[str | None] = mapped_column(String(255), nullable=True)
    latitude: Mapped[Decimal | None] = mapped_column(Numeric(9, 6), nullable=True)
    longitude: Mapped[Decimal | None] = mapped_column(Numeric(9, 6), nullable=True)
    elevation_ft: Mapped[int | None] = mapped_column(Integer, nullable=True)
    timezone: Mapped[str | None] = mapped_column(String(50), nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=datetime.utcnow
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=datetime.utcnow, onupdate=datetime.utcnow
    )

    __table_args__ = (
        Index("idx_airports_active", "is_active", postgresql_where=is_active == True),
    )


class MetarObservationModel(Base):
    """ORM model for metar_observations table."""

    __tablename__ = "metar_observations"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    icao_code: Mapped[str] = mapped_column(
        String(4), nullable=False, index=True
    )
    observation_time: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False
    )
    raw_metar: Mapped[str] = mapped_column(Text, nullable=False)

    # Wind data
    wind_direction_degrees: Mapped[int | None] = mapped_column(Integer, nullable=True)
    wind_speed_kt: Mapped[int | None] = mapped_column(Integer, nullable=True)
    wind_gust_kt: Mapped[int | None] = mapped_column(Integer, nullable=True)
    wind_variable_from: Mapped[int | None] = mapped_column(Integer, nullable=True)
    wind_variable_to: Mapped[int | None] = mapped_column(Integer, nullable=True)

    # Visibility
    visibility_statute_mi: Mapped[Decimal | None] = mapped_column(
        Numeric(5, 2), nullable=True
    )
    visibility_meters: Mapped[int | None] = mapped_column(Integer, nullable=True)

    # Weather and clouds (JSON)
    weather_phenomena: Mapped[dict[str, Any] | list[Any]] = mapped_column(
        JSONB, default=list
    )
    cloud_layers: Mapped[dict[str, Any] | list[Any]] = mapped_column(
        JSONB, default=list
    )
    ceiling_ft: Mapped[int | None] = mapped_column(Integer, nullable=True)

    # Temperature
    temperature_c: Mapped[Decimal | None] = mapped_column(Numeric(4, 1), nullable=True)
    dewpoint_c: Mapped[Decimal | None] = mapped_column(Numeric(4, 1), nullable=True)

    # Pressure
    altimeter_inhg: Mapped[Decimal | None] = mapped_column(Numeric(5, 2), nullable=True)
    altimeter_hpa: Mapped[int | None] = mapped_column(Integer, nullable=True)

    # Flight category
    flight_category: Mapped[str | None] = mapped_column(String(10), nullable=True)

    # Metadata
    source: Mapped[str] = mapped_column(String(50), nullable=False)
    fetched_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=datetime.utcnow
    )

    __table_args__ = (
        Index("idx_metar_icao_time", "icao_code", observation_time.desc()),
        Index("idx_metar_time", observation_time.desc()),
        Index("idx_metar_flight_category", "flight_category"),
        Index("idx_metar_fetched_at", fetched_at.desc()),
        # Unique constraint
        Index(
            "unique_metar_observation",
            "icao_code",
            "observation_time",
            unique=True,
        ),
    )


class CollectionLogModel(Base):
    """ORM model for collection_logs table."""

    __tablename__ = "collection_logs"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    started_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False
    )
    completed_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    status: Mapped[str] = mapped_column(String(20), nullable=False)
    airports_requested: Mapped[int] = mapped_column(Integer, default=0)
    airports_success: Mapped[int] = mapped_column(Integer, default=0)
    airports_failed: Mapped[int] = mapped_column(Integer, default=0)
    new_observations: Mapped[int] = mapped_column(Integer, default=0)
    duplicates_skipped: Mapped[int] = mapped_column(Integer, default=0)
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)
    details: Mapped[dict[str, Any]] = mapped_column(JSONB, default=dict)

    __table_args__ = (
        Index("idx_collection_logs_started_at", started_at.desc()),
        Index("idx_collection_logs_status", "status"),
    )
