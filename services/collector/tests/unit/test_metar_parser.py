"""Unit tests for METAR parser."""

from datetime import datetime, timezone
from decimal import Decimal

import pytest

from src.domain.interfaces import MetarParseError
from src.domain.value_objects import CloudCoverage, FlightCategoryType, WeatherIntensity
from src.infrastructure.parsers import MetarParser


@pytest.fixture
def parser():
    """Create a parser instance."""
    return MetarParser()


class TestMetarParserValidation:
    """Tests for METAR validation."""

    def test_validate_valid_metar(self, parser):
        """Test validation of a valid METAR."""
        metar = "KJFK 151856Z 31008KT 10SM FEW250 M01/M14 A3042"
        assert parser.validate(metar) is True

    def test_validate_empty_string(self, parser):
        """Test validation of empty string."""
        assert parser.validate("") is False
        assert parser.validate("   ") is False

    def test_validate_missing_icao(self, parser):
        """Test validation without ICAO code."""
        metar = "151856Z 31008KT 10SM"
        assert parser.validate(metar) is False

    def test_validate_missing_time(self, parser):
        """Test validation without observation time."""
        metar = "KJFK 31008KT 10SM"
        assert parser.validate(metar) is False


class TestMetarParserBasicParsing:
    """Tests for basic METAR parsing."""

    def test_parse_simple_metar(self, parser):
        """Test parsing a simple METAR."""
        metar = "KJFK 151856Z 31008KT 10SM FEW250 M01/M14 A3042"
        obs = parser.parse(metar, "test")

        assert obs.icao == "KJFK"
        assert obs.raw_metar == metar
        assert obs.source == "test"

    def test_parse_with_metar_prefix(self, parser):
        """Test parsing METAR with METAR/SPECI prefix."""
        metar = "METAR KJFK 151856Z 31008KT 10SM FEW250 M01/M14 A3042"
        obs = parser.parse(metar, "test")
        assert obs.icao == "KJFK"

        metar_speci = "SPECI EGLL 121530Z 24015G25KT 9999 SCT040"
        obs_speci = parser.parse(metar_speci, "test")
        assert obs_speci.icao == "EGLL"

    def test_parse_empty_raises_error(self, parser):
        """Test that parsing empty string raises error."""
        with pytest.raises(MetarParseError):
            parser.parse("", "test")

    def test_parse_invalid_icao_raises_error(self, parser):
        """Test that invalid ICAO raises error."""
        with pytest.raises(MetarParseError):
            parser.parse("1234 151856Z 31008KT", "test")


class TestMetarParserWind:
    """Tests for wind parsing."""

    def test_parse_wind_basic(self, parser):
        """Test basic wind parsing."""
        metar = "KJFK 151856Z 31008KT 10SM CLR 20/10 A3000"
        obs = parser.parse(metar, "test")

        assert obs.wind is not None
        assert obs.wind.direction_degrees == 310
        assert obs.wind.speed_kt == 8
        assert obs.wind.gust_kt is None

    def test_parse_wind_with_gusts(self, parser):
        """Test wind parsing with gusts."""
        metar = "KJFK 151856Z 27015G25KT 10SM CLR 20/10 A3000"
        obs = parser.parse(metar, "test")

        assert obs.wind.direction_degrees == 270
        assert obs.wind.speed_kt == 15
        assert obs.wind.gust_kt == 25

    def test_parse_wind_variable(self, parser):
        """Test variable wind parsing."""
        metar = "KJFK 151856Z VRB05KT 10SM CLR 20/10 A3000"
        obs = parser.parse(metar, "test")

        assert obs.wind.is_variable is True
        assert obs.wind.speed_kt == 5

    def test_parse_wind_calm(self, parser):
        """Test calm wind parsing."""
        metar = "KJFK 151856Z 00000KT 10SM CLR 20/10 A3000"
        obs = parser.parse(metar, "test")

        assert obs.wind.is_calm is True
        assert obs.wind.speed_kt == 0

    def test_parse_wind_variable_direction(self, parser):
        """Test wind with variable direction range."""
        metar = "KJFK 151856Z 31015KT 280V340 10SM CLR 20/10 A3000"
        obs = parser.parse(metar, "test")

        assert obs.wind.variable_from == 280
        assert obs.wind.variable_to == 340


class TestMetarParserVisibility:
    """Tests for visibility parsing."""

    def test_parse_visibility_statute_miles(self, parser):
        """Test visibility in statute miles."""
        metar = "KJFK 151856Z 31008KT 10SM CLR 20/10 A3000"
        obs = parser.parse(metar, "test")

        assert obs.visibility is not None
        assert obs.visibility.statute_miles == Decimal("10")

    def test_parse_visibility_greater_than_6sm(self, parser):
        """Test visibility greater than 6 SM."""
        metar = "KJFK 151856Z 31008KT P6SM CLR 20/10 A3000"
        obs = parser.parse(metar, "test")

        assert obs.visibility.is_greater_than is True
        assert obs.visibility.statute_miles == Decimal("6")

    def test_parse_visibility_fraction(self, parser):
        """Test fractional visibility."""
        metar = "KJFK 151856Z 31008KT 1/2SM FG 20/10 A3000"
        obs = parser.parse(metar, "test")

        assert obs.visibility.statute_miles == Decimal("0.5")

    def test_parse_visibility_mixed(self, parser):
        """Test mixed whole number and fraction visibility."""
        metar = "KJFK 151856Z 31008KT 2 1/2SM BR 20/10 A3000"
        obs = parser.parse(metar, "test")

        assert obs.visibility.statute_miles == Decimal("2.5")

    def test_parse_cavok(self, parser):
        """Test CAVOK visibility."""
        metar = "LFPG 151830Z 36012KT CAVOK 08/02 Q1024"
        obs = parser.parse(metar, "test")

        assert obs.visibility is not None
        assert obs.visibility.is_greater_than is True


class TestMetarParserClouds:
    """Tests for cloud layer parsing."""

    def test_parse_clouds_few(self, parser):
        """Test FEW cloud layer."""
        metar = "KJFK 151856Z 31008KT 10SM FEW020 20/10 A3000"
        obs = parser.parse(metar, "test")

        assert len(obs.cloud_layers) == 1
        assert obs.cloud_layers[0].coverage == CloudCoverage.FEW
        assert obs.cloud_layers[0].altitude_ft == 2000

    def test_parse_clouds_multiple_layers(self, parser):
        """Test multiple cloud layers."""
        metar = "KJFK 151856Z 31008KT 10SM FEW020 SCT050 BKN100 20/10 A3000"
        obs = parser.parse(metar, "test")

        assert len(obs.cloud_layers) == 3
        assert obs.cloud_layers[0].coverage == CloudCoverage.FEW
        assert obs.cloud_layers[1].coverage == CloudCoverage.SCT
        assert obs.cloud_layers[2].coverage == CloudCoverage.BKN

    def test_parse_clouds_with_cumulonimbus(self, parser):
        """Test cloud layer with CB."""
        metar = "KJFK 151856Z 31008KT 10SM SCT030CB 20/10 A3000"
        obs = parser.parse(metar, "test")

        assert obs.cloud_layers[0].cloud_type == "CB"
        assert obs.cloud_layers[0].is_cumulonimbus is True

    def test_parse_ceiling(self, parser):
        """Test ceiling calculation."""
        metar = "KJFK 151856Z 31008KT 10SM FEW010 BKN025 OVC040 20/10 A3000"
        obs = parser.parse(metar, "test")

        assert obs.ceiling_ft == 2500  # First BKN or OVC

    def test_parse_clear_sky(self, parser):
        """Test clear sky."""
        metar = "KJFK 151856Z 31008KT 10SM CLR 20/10 A3000"
        obs = parser.parse(metar, "test")

        assert len(obs.cloud_layers) == 1
        assert obs.cloud_layers[0].coverage == CloudCoverage.CLR


class TestMetarParserTemperature:
    """Tests for temperature parsing."""

    def test_parse_temperature_positive(self, parser):
        """Test positive temperature."""
        metar = "KJFK 151856Z 31008KT 10SM CLR 20/10 A3000"
        obs = parser.parse(metar, "test")

        assert obs.temperature_c == Decimal("20")
        assert obs.dewpoint_c == Decimal("10")

    def test_parse_temperature_negative(self, parser):
        """Test negative temperature."""
        metar = "KJFK 151856Z 31008KT 10SM CLR M05/M15 A3000"
        obs = parser.parse(metar, "test")

        assert obs.temperature_c == Decimal("-5")
        assert obs.dewpoint_c == Decimal("-15")

    def test_parse_temperature_mixed(self, parser):
        """Test mixed positive/negative temperature."""
        metar = "KJFK 151856Z 31008KT 10SM CLR 02/M01 A3000"
        obs = parser.parse(metar, "test")

        assert obs.temperature_c == Decimal("2")
        assert obs.dewpoint_c == Decimal("-1")


class TestMetarParserAltimeter:
    """Tests for altimeter parsing."""

    def test_parse_altimeter_us(self, parser):
        """Test US altimeter format."""
        metar = "KJFK 151856Z 31008KT 10SM CLR 20/10 A3042"
        obs = parser.parse(metar, "test")

        assert obs.altimeter_inhg == Decimal("30.42")
        assert obs.altimeter_hpa is not None

    def test_parse_altimeter_international(self, parser):
        """Test international altimeter format (Q)."""
        metar = "LFPG 151830Z 36012KT 9999 FEW040 08/02 Q1024"
        obs = parser.parse(metar, "test")

        assert obs.altimeter_hpa == 1024
        assert obs.altimeter_inhg is not None


class TestMetarParserWeather:
    """Tests for weather phenomena parsing."""

    def test_parse_weather_rain(self, parser):
        """Test rain weather."""
        metar = "KJFK 151856Z 31008KT 3SM RA 20/10 A3000"
        obs = parser.parse(metar, "test")

        assert len(obs.weather_phenomena) == 1
        assert obs.weather_phenomena[0].is_precipitation is True

    def test_parse_weather_heavy_rain(self, parser):
        """Test heavy rain."""
        metar = "KJFK 151856Z 31008KT 1SM +RA 20/10 A3000"
        obs = parser.parse(metar, "test")

        assert obs.weather_phenomena[0].intensity == WeatherIntensity.HEAVY

    def test_parse_weather_light_snow(self, parser):
        """Test light snow."""
        metar = "KJFK 151856Z 31008KT 2SM -SN 20/10 A3000"
        obs = parser.parse(metar, "test")

        assert obs.weather_phenomena[0].intensity == WeatherIntensity.LIGHT

    def test_parse_weather_thunderstorm(self, parser):
        """Test thunderstorm."""
        metar = "KJFK 151856Z 31008KT 5SM TSRA 20/10 A3000"
        obs = parser.parse(metar, "test")

        assert obs.weather_phenomena[0].is_thunderstorm is True

    def test_parse_weather_fog(self, parser):
        """Test fog."""
        metar = "KJFK 151856Z 31008KT 1/4SM FG 20/10 A3000"
        obs = parser.parse(metar, "test")

        assert obs.weather_phenomena[0].is_obscuration is True

    def test_parse_multiple_weather(self, parser):
        """Test multiple weather phenomena."""
        metar = "KJFK 151856Z 31008KT 2SM -RA BR 20/10 A3000"
        obs = parser.parse(metar, "test")

        assert len(obs.weather_phenomena) == 2


class TestMetarParserFlightCategory:
    """Tests for flight category calculation."""

    def test_flight_category_vfr(self, parser):
        """Test VFR conditions."""
        metar = "KJFK 151856Z 31008KT 10SM CLR 20/10 A3000"
        obs = parser.parse(metar, "test")

        assert obs.flight_category is not None
        assert obs.flight_category.category == FlightCategoryType.VFR

    def test_flight_category_mvfr_visibility(self, parser):
        """Test MVFR due to visibility."""
        metar = "KJFK 151856Z 31008KT 4SM CLR 20/10 A3000"
        obs = parser.parse(metar, "test")

        assert obs.flight_category.category == FlightCategoryType.MVFR

    def test_flight_category_mvfr_ceiling(self, parser):
        """Test MVFR due to ceiling."""
        metar = "KJFK 151856Z 31008KT 10SM BKN020 20/10 A3000"
        obs = parser.parse(metar, "test")

        assert obs.flight_category.category == FlightCategoryType.MVFR

    def test_flight_category_ifr(self, parser):
        """Test IFR conditions."""
        metar = "KJFK 151856Z 31008KT 2SM BKN008 20/10 A3000"
        obs = parser.parse(metar, "test")

        assert obs.flight_category.category == FlightCategoryType.IFR

    def test_flight_category_lifr(self, parser):
        """Test LIFR conditions."""
        metar = "KJFK 151856Z 31008KT 1/4SM OVC002 20/10 A3000"
        obs = parser.parse(metar, "test")

        assert obs.flight_category.category == FlightCategoryType.LIFR


class TestMetarParserRealExamples:
    """Tests with real-world METAR examples."""

    def test_real_jfk(self, parser):
        """Test real JFK METAR."""
        metar = "KJFK 151856Z 31008KT 10SM FEW250 M01/M14 A3042 RMK AO2 SLP314"
        obs = parser.parse(metar, "noaa_awc")

        assert obs.icao == "KJFK"
        assert obs.wind.direction_degrees == 310
        assert obs.wind.speed_kt == 8
        assert obs.temperature_c == Decimal("-1")
        assert obs.dewpoint_c == Decimal("-14")
        assert obs.altimeter_inhg == Decimal("30.42")

    def test_real_paris(self, parser):
        """Test real Paris CDG METAR."""
        metar = "LFPG 151830Z 36012KT 9999 FEW040 BKN100 08/02 Q1024 TEMPO 4000 BR"
        obs = parser.parse(metar, "noaa_awc")

        assert obs.icao == "LFPG"
        assert obs.wind.direction_degrees == 360
        assert obs.wind.speed_kt == 12
        assert obs.altimeter_hpa == 1024

    def test_real_heathrow(self, parser):
        """Test real London Heathrow METAR."""
        metar = "EGLL 151850Z AUTO 24015G25KT 200V280 9999 -SHRA FEW018 SCT025CB BKN040 09/06 Q1015"
        obs = parser.parse(metar, "noaa_awc")

        assert obs.icao == "EGLL"
        assert obs.wind.direction_degrees == 240
        assert obs.wind.speed_kt == 15
        assert obs.wind.gust_kt == 25
        assert obs.wind.variable_from == 200
        assert obs.wind.variable_to == 280
        assert obs.has_precipitation is True
