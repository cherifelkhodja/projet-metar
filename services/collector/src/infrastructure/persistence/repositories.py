"""SQLAlchemy repository implementations."""

from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from typing import Any

import structlog
from sqlalchemy import delete, func, select
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.ext.asyncio import AsyncSession

from src.domain.entities import Airport, CollectionLog, CollectionStatus, MetarObservation
from src.domain.interfaces import (
    IAirportRepository,
    ICollectionLogRepository,
    IMetarObservationRepository,
)
from src.domain.value_objects import (
    CloudCoverage,
    CloudLayer,
    FlightCategory,
    ICAOCode,
    Visibility,
    WeatherPhenomenon,
    Wind,
)

from .database import Database
from .models import AirportModel, CollectionLogModel, MetarObservationModel

logger = structlog.get_logger(__name__)


class SQLAlchemyAirportRepository(IAirportRepository):
    """SQLAlchemy implementation of the airport repository."""

    def __init__(self, database: Database):
        self._database = database

    async def get_by_icao(self, icao_code: ICAOCode | str) -> Airport | None:
        """Retrieve an airport by its ICAO code."""
        icao = str(icao_code).upper()

        async with self._database.session() as session:
            result = await session.execute(
                select(AirportModel).where(AirportModel.icao_code == icao)
            )
            model = result.scalar_one_or_none()

            if model is None:
                return None

            return self._to_entity(model)

    async def get_all(self, active_only: bool = True) -> list[Airport]:
        """Retrieve all airports."""
        async with self._database.session() as session:
            query = select(AirportModel)
            if active_only:
                query = query.where(AirportModel.is_active == True)
            query = query.order_by(AirportModel.icao_code)

            result = await session.execute(query)
            models = result.scalars().all()

            return [self._to_entity(model) for model in models]

    async def save(self, airport: Airport) -> Airport:
        """Save or update an airport."""
        async with self._database.session() as session:
            stmt = insert(AirportModel).values(
                icao_code=str(airport.icao_code),
                name=airport.name,
                latitude=airport.latitude,
                longitude=airport.longitude,
                elevation_ft=airport.elevation_ft,
                timezone=airport.timezone,
                is_active=airport.is_active,
            )
            stmt = stmt.on_conflict_do_update(
                index_elements=["icao_code"],
                set_={
                    "name": stmt.excluded.name,
                    "latitude": stmt.excluded.latitude,
                    "longitude": stmt.excluded.longitude,
                    "elevation_ft": stmt.excluded.elevation_ft,
                    "timezone": stmt.excluded.timezone,
                    "is_active": stmt.excluded.is_active,
                    "updated_at": datetime.utcnow(),
                },
            )
            await session.execute(stmt)

        return airport

    async def delete(self, icao_code: ICAOCode | str) -> bool:
        """Delete an airport."""
        icao = str(icao_code).upper()

        async with self._database.session() as session:
            result = await session.execute(
                delete(AirportModel).where(AirportModel.icao_code == icao)
            )
            return result.rowcount > 0

    async def exists(self, icao_code: ICAOCode | str) -> bool:
        """Check if an airport exists."""
        icao = str(icao_code).upper()

        async with self._database.session() as session:
            result = await session.execute(
                select(func.count()).where(AirportModel.icao_code == icao)
            )
            return result.scalar_one() > 0

    async def count(self, active_only: bool = True) -> int:
        """Count airports."""
        async with self._database.session() as session:
            query = select(func.count()).select_from(AirportModel)
            if active_only:
                query = query.where(AirportModel.is_active == True)

            result = await session.execute(query)
            return result.scalar_one()

    def _to_entity(self, model: AirportModel) -> Airport:
        """Convert ORM model to domain entity."""
        return Airport(
            icao_code=ICAOCode(model.icao_code),
            name=model.name,
            latitude=model.latitude,
            longitude=model.longitude,
            elevation_ft=model.elevation_ft,
            timezone=model.timezone,
            is_active=model.is_active,
            created_at=model.created_at,
            updated_at=model.updated_at,
        )


class SQLAlchemyMetarObservationRepository(IMetarObservationRepository):
    """SQLAlchemy implementation of the METAR observation repository."""

    def __init__(self, database: Database):
        self._database = database

    async def save(self, observation: MetarObservation) -> MetarObservation:
        """Save a METAR observation."""
        async with self._database.session() as session:
            model = self._to_model(observation)
            session.add(model)
            await session.flush()
            observation.id = model.id
            return observation

    async def save_batch(self, observations: list[MetarObservation]) -> int:
        """Save multiple observations using upsert."""
        if not observations:
            return 0

        saved_count = 0

        async with self._database.session() as session:
            for obs in observations:
                stmt = insert(MetarObservationModel).values(
                    icao_code=str(obs.icao_code),
                    observation_time=obs.observation_time,
                    raw_metar=obs.raw_metar,
                    wind_direction_degrees=obs.wind_direction_degrees,
                    wind_speed_kt=obs.wind_speed_kt,
                    wind_gust_kt=obs.wind_gust_kt,
                    wind_variable_from=obs.wind.variable_from if obs.wind else None,
                    wind_variable_to=obs.wind.variable_to if obs.wind else None,
                    visibility_statute_mi=obs.visibility_statute_mi,
                    visibility_meters=obs.visibility_meters,
                    weather_phenomena=obs.weather_phenomena_to_json(),
                    cloud_layers=obs.cloud_layers_to_json(),
                    ceiling_ft=obs.ceiling_ft,
                    temperature_c=obs.temperature_c,
                    dewpoint_c=obs.dewpoint_c,
                    altimeter_inhg=obs.altimeter_inhg,
                    altimeter_hpa=obs.altimeter_hpa,
                    flight_category=obs.flight_category_str,
                    source=obs.source,
                    fetched_at=obs.fetched_at,
                )
                stmt = stmt.on_conflict_do_nothing(
                    index_elements=["icao_code", "observation_time"]
                )
                result = await session.execute(stmt)
                if result.rowcount > 0:
                    saved_count += 1

        return saved_count

    async def get_latest(self, icao_code: ICAOCode | str) -> MetarObservation | None:
        """Get the latest METAR for an airport."""
        icao = str(icao_code).upper()

        async with self._database.session() as session:
            result = await session.execute(
                select(MetarObservationModel)
                .where(MetarObservationModel.icao_code == icao)
                .order_by(MetarObservationModel.observation_time.desc())
                .limit(1)
            )
            model = result.scalar_one_or_none()

            if model is None:
                return None

            return self._to_entity(model)

    async def get_latest_bulk(
        self, icao_codes: list[ICAOCode | str] | None = None
    ) -> list[MetarObservation]:
        """Get the latest METAR for multiple airports."""
        async with self._database.session() as session:
            # Subquery to get latest observation time per airport
            subquery = (
                select(
                    MetarObservationModel.icao_code,
                    func.max(MetarObservationModel.observation_time).label("max_time"),
                )
                .group_by(MetarObservationModel.icao_code)
            )

            if icao_codes:
                icao_list = [str(code).upper() for code in icao_codes]
                subquery = subquery.where(
                    MetarObservationModel.icao_code.in_(icao_list)
                )

            subquery = subquery.subquery()

            # Main query joining with subquery
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

            return [self._to_entity(model) for model in models]

    async def get_history(
        self,
        icao_code: ICAOCode | str,
        start_date: datetime | None = None,
        end_date: datetime | None = None,
        page: int = 1,
        per_page: int = 50,
    ) -> tuple[list[MetarObservation], int]:
        """Get historical observations with pagination."""
        icao = str(icao_code).upper()
        offset = (page - 1) * per_page

        async with self._database.session() as session:
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

            observations = [self._to_entity(model) for model in models]
            return observations, total

    async def exists(self, icao_code: ICAOCode | str, observation_time: datetime) -> bool:
        """Check if an observation already exists."""
        icao = str(icao_code).upper()

        async with self._database.session() as session:
            result = await session.execute(
                select(func.count()).where(
                    (MetarObservationModel.icao_code == icao)
                    & (MetarObservationModel.observation_time == observation_time)
                )
            )
            return result.scalar_one() > 0

    async def count(
        self,
        icao_code: ICAOCode | str | None = None,
        start_date: datetime | None = None,
        end_date: datetime | None = None,
    ) -> int:
        """Count observations."""
        async with self._database.session() as session:
            query = select(func.count()).select_from(MetarObservationModel)

            if icao_code:
                query = query.where(
                    MetarObservationModel.icao_code == str(icao_code).upper()
                )
            if start_date:
                query = query.where(MetarObservationModel.observation_time >= start_date)
            if end_date:
                query = query.where(MetarObservationModel.observation_time <= end_date)

            result = await session.execute(query)
            return result.scalar_one()

    async def delete_before(self, cutoff_date: datetime) -> int:
        """Delete observations before a date."""
        async with self._database.session() as session:
            result = await session.execute(
                delete(MetarObservationModel).where(
                    MetarObservationModel.observation_time < cutoff_date
                )
            )
            return result.rowcount

    def _to_model(self, entity: MetarObservation) -> MetarObservationModel:
        """Convert domain entity to ORM model."""
        return MetarObservationModel(
            icao_code=str(entity.icao_code),
            observation_time=entity.observation_time,
            raw_metar=entity.raw_metar,
            wind_direction_degrees=entity.wind_direction_degrees,
            wind_speed_kt=entity.wind_speed_kt,
            wind_gust_kt=entity.wind_gust_kt,
            wind_variable_from=entity.wind.variable_from if entity.wind else None,
            wind_variable_to=entity.wind.variable_to if entity.wind else None,
            visibility_statute_mi=entity.visibility_statute_mi,
            visibility_meters=entity.visibility_meters,
            weather_phenomena=entity.weather_phenomena_to_json(),
            cloud_layers=entity.cloud_layers_to_json(),
            ceiling_ft=entity.ceiling_ft,
            temperature_c=entity.temperature_c,
            dewpoint_c=entity.dewpoint_c,
            altimeter_inhg=entity.altimeter_inhg,
            altimeter_hpa=entity.altimeter_hpa,
            flight_category=entity.flight_category_str,
            source=entity.source,
            fetched_at=entity.fetched_at,
        )

    def _to_entity(self, model: MetarObservationModel) -> MetarObservation:
        """Convert ORM model to domain entity."""
        # Reconstruct wind
        wind = None
        if model.wind_speed_kt is not None:
            if model.wind_speed_kt == 0 and model.wind_direction_degrees is None:
                wind = Wind.calm()
            elif model.wind_direction_degrees is None:
                wind = Wind.variable(
                    model.wind_speed_kt,
                    model.wind_gust_kt,
                )
            else:
                wind = Wind(
                    direction_degrees=model.wind_direction_degrees,
                    speed_kt=model.wind_speed_kt,
                    gust_kt=model.wind_gust_kt,
                    variable_from=model.wind_variable_from,
                    variable_to=model.wind_variable_to,
                )

        # Reconstruct visibility
        visibility = None
        if model.visibility_statute_mi is not None:
            visibility = Visibility(
                statute_miles=model.visibility_statute_mi,
                meters=model.visibility_meters,
            )
        elif model.visibility_meters is not None:
            visibility = Visibility.from_meters(model.visibility_meters)

        # Reconstruct weather phenomena
        weather_phenomena = []
        for wp_data in model.weather_phenomena or []:
            if isinstance(wp_data, dict) and "raw" in wp_data:
                try:
                    weather_phenomena.append(WeatherPhenomenon.from_code(wp_data["raw"]))
                except ValueError:
                    pass

        # Reconstruct cloud layers
        cloud_layers = []
        for cl_data in model.cloud_layers or []:
            if isinstance(cl_data, dict) and "coverage" in cl_data:
                try:
                    cloud_layers.append(
                        CloudLayer(
                            coverage=CloudCoverage.from_string(cl_data["coverage"]),
                            altitude_ft=cl_data.get("altitude_ft"),
                            cloud_type=cl_data.get("cloud_type"),
                        )
                    )
                except ValueError:
                    pass

        return MetarObservation(
            id=model.id,
            icao_code=ICAOCode(model.icao_code),
            observation_time=model.observation_time,
            raw_metar=model.raw_metar,
            source=model.source,
            wind=wind,
            visibility=visibility,
            weather_phenomena=weather_phenomena,
            cloud_layers=cloud_layers,
            temperature_c=model.temperature_c,
            dewpoint_c=model.dewpoint_c,
            altimeter_inhg=model.altimeter_inhg,
            altimeter_hpa=model.altimeter_hpa,
            fetched_at=model.fetched_at,
        )


class SQLAlchemyCollectionLogRepository(ICollectionLogRepository):
    """SQLAlchemy implementation of the collection log repository."""

    def __init__(self, database: Database):
        self._database = database

    async def save(self, log: CollectionLog) -> CollectionLog:
        """Save or update a collection log."""
        async with self._database.session() as session:
            if log.id is None:
                # Insert new
                model = CollectionLogModel(
                    started_at=log.started_at,
                    completed_at=log.completed_at,
                    status=log.status.value,
                    airports_requested=log.airports_requested,
                    airports_success=log.airports_success,
                    airports_failed=log.airports_failed,
                    new_observations=log.new_observations,
                    duplicates_skipped=log.duplicates_skipped,
                    error_message=log.error_message,
                    details=log.details,
                )
                session.add(model)
                await session.flush()
                log.id = model.id
            else:
                # Update existing
                result = await session.execute(
                    select(CollectionLogModel).where(CollectionLogModel.id == log.id)
                )
                model = result.scalar_one_or_none()
                if model:
                    model.completed_at = log.completed_at
                    model.status = log.status.value
                    model.airports_requested = log.airports_requested
                    model.airports_success = log.airports_success
                    model.airports_failed = log.airports_failed
                    model.new_observations = log.new_observations
                    model.duplicates_skipped = log.duplicates_skipped
                    model.error_message = log.error_message
                    model.details = log.details

            return log

    async def get_latest(self) -> CollectionLog | None:
        """Get the most recent collection log."""
        async with self._database.session() as session:
            result = await session.execute(
                select(CollectionLogModel)
                .order_by(CollectionLogModel.started_at.desc())
                .limit(1)
            )
            model = result.scalar_one_or_none()

            if model is None:
                return None

            return self._to_entity(model)

    async def get_running(self) -> CollectionLog | None:
        """Get currently running collection."""
        async with self._database.session() as session:
            result = await session.execute(
                select(CollectionLogModel)
                .where(CollectionLogModel.status == "running")
                .order_by(CollectionLogModel.started_at.desc())
                .limit(1)
            )
            model = result.scalar_one_or_none()

            if model is None:
                return None

            return self._to_entity(model)

    async def get_history(
        self,
        page: int = 1,
        per_page: int = 20,
    ) -> tuple[list[CollectionLog], int]:
        """Get collection history with pagination."""
        offset = (page - 1) * per_page

        async with self._database.session() as session:
            # Count
            count_result = await session.execute(
                select(func.count()).select_from(CollectionLogModel)
            )
            total = count_result.scalar_one()

            # Data
            result = await session.execute(
                select(CollectionLogModel)
                .order_by(CollectionLogModel.started_at.desc())
                .offset(offset)
                .limit(per_page)
            )
            models = result.scalars().all()

            logs = [self._to_entity(model) for model in models]
            return logs, total

    async def get_statistics(
        self,
        start_date: datetime | None = None,
        end_date: datetime | None = None,
    ) -> dict[str, int | float]:
        """Get aggregate statistics."""
        async with self._database.session() as session:
            query = select(
                func.count().label("total_runs"),
                func.sum(CollectionLogModel.new_observations).label("total_observations"),
                func.sum(CollectionLogModel.airports_success).label("total_success"),
                func.sum(CollectionLogModel.airports_failed).label("total_failed"),
                func.avg(CollectionLogModel.new_observations).label("avg_observations"),
            ).select_from(CollectionLogModel)

            if start_date:
                query = query.where(CollectionLogModel.started_at >= start_date)
            if end_date:
                query = query.where(CollectionLogModel.started_at <= end_date)

            result = await session.execute(query)
            row = result.one()

            return {
                "total_runs": row.total_runs or 0,
                "total_observations": int(row.total_observations or 0),
                "total_success": int(row.total_success or 0),
                "total_failed": int(row.total_failed or 0),
                "avg_observations_per_run": float(row.avg_observations or 0),
            }

    def _to_entity(self, model: CollectionLogModel) -> CollectionLog:
        """Convert ORM model to domain entity."""
        return CollectionLog(
            id=model.id,
            started_at=model.started_at,
            completed_at=model.completed_at,
            status=CollectionStatus(model.status),
            airports_requested=model.airports_requested,
            airports_success=model.airports_success,
            airports_failed=model.airports_failed,
            new_observations=model.new_observations,
            duplicates_skipped=model.duplicates_skipped,
            error_message=model.error_message,
            details=model.details or {},
        )
