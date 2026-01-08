"""Unit tests for domain value objects."""

from decimal import Decimal

import pytest

from src.domain.value_objects import (
    CloudCoverage,
    CloudLayer,
    FlightCategory,
    ICAOCode,
    Visibility,
    WeatherPhenomenon,
    Wind,
)


class TestICAOCode:
    """Tests for ICAOCode value object."""

    def test_create_valid_icao(self):
        """Test creating a valid ICAO code."""
        icao = ICAOCode("KJFK")
        assert icao.value == "KJFK"

    def test_create_lowercase_normalized(self):
        """Test lowercase is normalized to uppercase."""
        icao = ICAOCode("kjfk")
        assert icao.value == "KJFK"

    def test_create_with_spaces_stripped(self):
        """Test spaces are stripped."""
        icao = ICAOCode("  KJFK  ")
        assert icao.value == "KJFK"

    def test_invalid_length_raises_error(self):
        """Test invalid length raises error."""
        with pytest.raises(ValueError):
            ICAOCode("JFK")
        with pytest.raises(ValueError):
            ICAOCode("KJFKX")

    def test_invalid_characters_raises_error(self):
        """Test invalid characters raise error."""
        with pytest.raises(ValueError):
            ICAOCode("KJF1")
        with pytest.raises(ValueError):
            ICAOCode("KJ-K")

    def test_equality(self):
        """Test ICAO code equality."""
        icao1 = ICAOCode("KJFK")
        icao2 = ICAOCode("KJFK")
        icao3 = ICAOCode("KLAX")

        assert icao1 == icao2
        assert icao1 != icao3
        assert icao1 == "KJFK"

    def test_hash(self):
        """Test ICAO code hashing."""
        icao1 = ICAOCode("KJFK")
        icao2 = ICAOCode("KJFK")

        assert hash(icao1) == hash(icao2)
        assert len({icao1, icao2}) == 1


class TestWind:
    """Tests for Wind value object."""

    def test_create_basic_wind(self):
        """Test creating basic wind."""
        wind = Wind(direction_degrees=310, speed_kt=15)
        assert wind.direction_degrees == 310
        assert wind.speed_kt == 15
        assert wind.gust_kt is None

    def test_create_wind_with_gusts(self):
        """Test wind with gusts."""
        wind = Wind(direction_degrees=270, speed_kt=20, gust_kt=35)
        assert wind.has_gusts is True
        assert wind.gust_kt == 35

    def test_calm_wind(self):
        """Test calm wind."""
        wind = Wind.calm()
        assert wind.is_calm is True
        assert wind.speed_kt == 0

    def test_variable_wind(self):
        """Test variable wind."""
        wind = Wind.variable(speed_kt=10, gust_kt=20)
        assert wind.is_variable is True
        assert wind.direction_degrees is None

    def test_invalid_speed_raises_error(self):
        """Test negative speed raises error."""
        with pytest.raises(ValueError):
            Wind(direction_degrees=270, speed_kt=-5)

    def test_invalid_gust_raises_error(self):
        """Test gust less than speed raises error."""
        with pytest.raises(ValueError):
            Wind(direction_degrees=270, speed_kt=20, gust_kt=15)

    def test_invalid_direction_raises_error(self):
        """Test invalid direction raises error."""
        with pytest.raises(ValueError):
            Wind(direction_degrees=400, speed_kt=10)

    def test_speed_conversion(self):
        """Test speed unit conversions."""
        wind = Wind(direction_degrees=180, speed_kt=20)
        assert wind.speed_mps == pytest.approx(10.29, rel=0.01)
        assert wind.speed_kmh == pytest.approx(37.04, rel=0.01)


class TestVisibility:
    """Tests for Visibility value object."""

    def test_create_from_statute_miles(self):
        """Test creating from statute miles."""
        vis = Visibility.from_statute_miles(10)
        assert vis.statute_miles == Decimal("10")
        assert vis.meters is not None

    def test_create_from_meters(self):
        """Test creating from meters."""
        vis = Visibility.from_meters(5000)
        assert vis.meters == 5000
        assert vis.statute_miles is not None

    def test_unlimited_visibility(self):
        """Test unlimited visibility."""
        vis = Visibility.unlimited()
        assert vis.is_greater_than is True

    def test_low_visibility(self):
        """Test low visibility detection."""
        vis = Visibility.from_statute_miles(2)
        assert vis.is_low is True

    def test_very_low_visibility(self):
        """Test very low visibility detection."""
        vis = Visibility.from_statute_miles(Decimal("0.5"))
        assert vis.is_very_low is True

    def test_no_value_raises_error(self):
        """Test that no value raises error."""
        with pytest.raises(ValueError):
            Visibility()


class TestCloudLayer:
    """Tests for CloudLayer value object."""

    def test_create_cloud_layer(self):
        """Test creating cloud layer."""
        layer = CloudLayer(coverage=CloudCoverage.SCT, altitude_ft=5000)
        assert layer.coverage == CloudCoverage.SCT
        assert layer.altitude_ft == 5000

    def test_cloud_with_cb(self):
        """Test cloud layer with CB."""
        layer = CloudLayer(coverage=CloudCoverage.BKN, altitude_ft=3000, cloud_type="CB")
        assert layer.is_cumulonimbus is True

    def test_cloud_with_tcu(self):
        """Test cloud layer with TCU."""
        layer = CloudLayer(coverage=CloudCoverage.SCT, altitude_ft=4000, cloud_type="TCU")
        assert layer.is_towering_cumulus is True

    def test_ceiling_detection(self):
        """Test ceiling detection."""
        bkn = CloudLayer(coverage=CloudCoverage.BKN, altitude_ft=2000)
        ovc = CloudLayer(coverage=CloudCoverage.OVC, altitude_ft=3000)
        sct = CloudLayer(coverage=CloudCoverage.SCT, altitude_ft=1000)

        assert bkn.coverage.is_ceiling is True
        assert ovc.coverage.is_ceiling is True
        assert sct.coverage.is_ceiling is False

    def test_invalid_cloud_type(self):
        """Test invalid cloud type."""
        with pytest.raises(ValueError):
            CloudLayer(coverage=CloudCoverage.BKN, altitude_ft=3000, cloud_type="INVALID")


class TestWeatherPhenomenon:
    """Tests for WeatherPhenomenon value object."""

    def test_parse_rain(self):
        """Test parsing rain."""
        wp = WeatherPhenomenon.from_code("RA")
        assert wp.is_precipitation is True
        assert "RA" in wp.phenomena

    def test_parse_heavy_rain(self):
        """Test parsing heavy rain."""
        from src.domain.value_objects import WeatherIntensity
        wp = WeatherPhenomenon.from_code("+RA")
        assert wp.intensity == WeatherIntensity.HEAVY

    def test_parse_light_snow(self):
        """Test parsing light snow."""
        from src.domain.value_objects import WeatherIntensity
        wp = WeatherPhenomenon.from_code("-SN")
        assert wp.intensity == WeatherIntensity.LIGHT

    def test_parse_thunderstorm_rain(self):
        """Test parsing thunderstorm with rain."""
        wp = WeatherPhenomenon.from_code("TSRA")
        assert wp.is_thunderstorm is True
        assert wp.is_precipitation is True

    def test_parse_fog(self):
        """Test parsing fog."""
        wp = WeatherPhenomenon.from_code("FG")
        assert wp.is_obscuration is True

    def test_parse_freezing_rain(self):
        """Test parsing freezing rain."""
        wp = WeatherPhenomenon.from_code("FZRA")
        assert wp.is_freezing is True
        assert wp.is_precipitation is True


class TestFlightCategory:
    """Tests for FlightCategory value object."""

    def test_vfr_conditions(self):
        """Test VFR conditions."""
        vis = Visibility.from_statute_miles(10)
        clouds = [CloudLayer(coverage=CloudCoverage.FEW, altitude_ft=5000)]

        fc = FlightCategory.calculate(vis, clouds)
        assert fc.category.value == "VFR"

    def test_mvfr_visibility(self):
        """Test MVFR due to visibility."""
        vis = Visibility.from_statute_miles(4)
        clouds = [CloudLayer(coverage=CloudCoverage.CLR)]

        fc = FlightCategory.calculate(vis, clouds)
        assert fc.category.value == "MVFR"

    def test_mvfr_ceiling(self):
        """Test MVFR due to ceiling."""
        vis = Visibility.from_statute_miles(10)
        clouds = [CloudLayer(coverage=CloudCoverage.BKN, altitude_ft=2500)]

        fc = FlightCategory.calculate(vis, clouds)
        assert fc.category.value == "MVFR"

    def test_ifr_conditions(self):
        """Test IFR conditions."""
        vis = Visibility.from_statute_miles(2)
        clouds = [CloudLayer(coverage=CloudCoverage.OVC, altitude_ft=800)]

        fc = FlightCategory.calculate(vis, clouds)
        assert fc.category.value == "IFR"

    def test_lifr_conditions(self):
        """Test LIFR conditions."""
        vis = Visibility.from_statute_miles(Decimal("0.5"))
        clouds = [CloudLayer(coverage=CloudCoverage.OVC, altitude_ft=300)]

        fc = FlightCategory.calculate(vis, clouds)
        assert fc.category.value == "LIFR"

    def test_worst_condition_wins(self):
        """Test that worst condition determines category."""
        # Good visibility but low ceiling
        vis = Visibility.from_statute_miles(10)
        clouds = [CloudLayer(coverage=CloudCoverage.BKN, altitude_ft=400)]

        fc = FlightCategory.calculate(vis, clouds)
        assert fc.category.value == "LIFR"  # Ceiling is limiting factor
