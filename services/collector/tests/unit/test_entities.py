"""Unit tests for domain entities."""

from datetime import datetime
from decimal import Decimal

import pytest

from src.domain.entities import Airport, CollectionLog, CollectionStatus, MetarObservation
from src.domain.value_objects import ICAOCode, Visibility, Wind


class TestAirport:
    """Tests for Airport entity."""

    def test_create_airport(self):
        """Test creating an airport."""
        airport = Airport.create(
            icao_code="KJFK",
            name="John F. Kennedy International Airport",
            latitude=40.6413,
            longitude=-73.7781,
            elevation_ft=13,
        )

        assert airport.icao == "KJFK"
        assert airport.name == "John F. Kennedy International Airport"
        assert airport.latitude == Decimal("40.6413")
        assert airport.is_active is True

    def test_create_from_icao_code(self):
        """Test creating with ICAOCode object."""
        icao = ICAOCode("LFPG")
        airport = Airport.create(icao_code=icao, name="Paris CDG")

        assert airport.icao == "LFPG"

    def test_activate_deactivate(self):
        """Test activate/deactivate methods."""
        airport = Airport.create(icao_code="KJFK")

        airport.deactivate()
        assert airport.is_active is False

        airport.activate()
        assert airport.is_active is True

    def test_update_location(self):
        """Test updating location."""
        airport = Airport.create(icao_code="KJFK")
        airport.update_location(
            latitude=40.6413,
            longitude=-73.7781,
            elevation_ft=13,
        )

        assert airport.latitude == Decimal("40.6413")
        assert airport.longitude == Decimal("-73.7781")
        assert airport.elevation_ft == 13

    def test_equality(self):
        """Test airport equality."""
        airport1 = Airport.create(icao_code="KJFK", name="JFK")
        airport2 = Airport.create(icao_code="KJFK", name="Kennedy")
        airport3 = Airport.create(icao_code="KLAX", name="LAX")

        assert airport1 == airport2
        assert airport1 != airport3

    def test_invalid_latitude(self):
        """Test invalid latitude."""
        with pytest.raises(ValueError):
            Airport.create(icao_code="KJFK", latitude=100)

    def test_invalid_longitude(self):
        """Test invalid longitude."""
        with pytest.raises(ValueError):
            Airport.create(icao_code="KJFK", longitude=200)


class TestMetarObservation:
    """Tests for MetarObservation entity."""

    def test_create_observation(self):
        """Test creating an observation."""
        obs = MetarObservation.create(
            icao_code="KJFK",
            observation_time=datetime(2024, 1, 15, 18, 56),
            raw_metar="KJFK 151856Z 31008KT 10SM CLR 20/10 A3000",
            source="test",
        )

        assert obs.icao == "KJFK"
        assert obs.raw_metar == "KJFK 151856Z 31008KT 10SM CLR 20/10 A3000"
        assert obs.source == "test"

    def test_observation_with_wind(self):
        """Test observation with wind data."""
        wind = Wind(direction_degrees=310, speed_kt=8)
        obs = MetarObservation.create(
            icao_code="KJFK",
            observation_time=datetime.utcnow(),
            raw_metar="KJFK 151856Z 31008KT 10SM CLR 20/10 A3000",
            source="test",
            wind=wind,
        )

        assert obs.wind_direction_degrees == 310
        assert obs.wind_speed_kt == 8

    def test_observation_with_visibility(self):
        """Test observation with visibility."""
        visibility = Visibility.from_statute_miles(10)
        obs = MetarObservation.create(
            icao_code="KJFK",
            observation_time=datetime.utcnow(),
            raw_metar="test",
            source="test",
            visibility=visibility,
        )

        assert obs.visibility_statute_mi == Decimal("10")

    def test_observation_equality(self):
        """Test observation equality (based on ICAO and time)."""
        time = datetime(2024, 1, 15, 18, 56)

        obs1 = MetarObservation.create(
            icao_code="KJFK",
            observation_time=time,
            raw_metar="metar1",
            source="test1",
        )
        obs2 = MetarObservation.create(
            icao_code="KJFK",
            observation_time=time,
            raw_metar="metar2",
            source="test2",
        )
        obs3 = MetarObservation.create(
            icao_code="KLAX",
            observation_time=time,
            raw_metar="metar3",
            source="test3",
        )

        assert obs1 == obs2  # Same ICAO and time
        assert obs1 != obs3  # Different ICAO

    def test_flight_category_calculated(self):
        """Test that flight category is auto-calculated."""
        visibility = Visibility.from_statute_miles(10)
        obs = MetarObservation.create(
            icao_code="KJFK",
            observation_time=datetime.utcnow(),
            raw_metar="test",
            source="test",
            visibility=visibility,
        )

        assert obs.flight_category is not None
        assert obs.flight_category_str == "VFR"


class TestCollectionLog:
    """Tests for CollectionLog entity."""

    def test_start_collection(self):
        """Test starting a collection."""
        log = CollectionLog.start(airports_count=10)

        assert log.status == CollectionStatus.RUNNING
        assert log.airports_requested == 10
        assert log.is_running is True

    def test_record_success(self):
        """Test recording success."""
        log = CollectionLog.start(airports_count=5)
        log.record_success("KJFK")
        log.record_success("KLAX")

        assert log.airports_success == 2
        assert "KJFK" in log.details.get("successful_airports", [])

    def test_record_failure(self):
        """Test recording failure."""
        log = CollectionLog.start(airports_count=5)
        log.record_failure("KJFK", "Connection error")

        assert log.airports_failed == 1
        assert "KJFK" in log.details.get("failed_airports", {})

    def test_record_observations(self):
        """Test recording observations."""
        log = CollectionLog.start(airports_count=5)
        log.record_new_observation()
        log.record_new_observation()
        log.record_duplicate()

        assert log.new_observations == 2
        assert log.duplicates_skipped == 1

    def test_complete_success(self):
        """Test completing with success."""
        log = CollectionLog.start(airports_count=5)
        for i in range(5):
            log.record_success(f"ICAO{i}")
        log.complete()

        assert log.status == CollectionStatus.SUCCESS
        assert log.is_complete is True
        assert log.completed_at is not None

    def test_complete_partial(self):
        """Test completing with partial success."""
        log = CollectionLog.start(airports_count=5)
        log.record_success("KJFK")
        log.record_failure("KLAX", "Error")
        log.complete()

        assert log.status == CollectionStatus.PARTIAL

    def test_complete_failed(self):
        """Test completing with failure."""
        log = CollectionLog.start(airports_count=5)
        log.complete(error_message="Total failure")

        assert log.status == CollectionStatus.FAILED
        assert log.error_message == "Total failure"

    def test_success_rate(self):
        """Test success rate calculation."""
        log = CollectionLog.start(airports_count=10)
        for i in range(7):
            log.record_success(f"ICAO{i}")
        for i in range(3):
            log.record_failure(f"FAIL{i}", "Error")

        assert log.success_rate == 70.0

    def test_duration(self):
        """Test duration calculation."""
        log = CollectionLog.start(airports_count=5)
        log.complete()

        assert log.duration_seconds is not None
        assert log.duration_seconds >= 0
