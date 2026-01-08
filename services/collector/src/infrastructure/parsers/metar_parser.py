"""METAR parser implementation."""

from __future__ import annotations

import re
from datetime import datetime, timezone
from decimal import Decimal, InvalidOperation
from typing import Match

from src.domain.entities import MetarObservation
from src.domain.interfaces import IMetarParser, MetarParseError
from src.domain.value_objects import (
    CloudCoverage,
    CloudLayer,
    ICAOCode,
    Visibility,
    WeatherPhenomenon,
    Wind,
)


class MetarParser(IMetarParser):
    """Parser for raw METAR strings into structured MetarObservation objects.

    Handles both US (TAF/METAR) and international METAR formats.

    Example METAR:
        KJFK 151856Z 31008KT 10SM FEW250 M01/M14 A3042 RMK AO2 SLP314
        LFPG 151830Z 36012KT 9999 FEW040 BKN100 08/02 Q1024 TEMPO 4000 BR
    """

    # Regex patterns for METAR components
    ICAO_PATTERN = re.compile(r"^([A-Z]{4})\b")
    TIME_PATTERN = re.compile(r"\b(\d{2})(\d{2})(\d{2})Z\b")

    # Wind patterns
    WIND_PATTERN = re.compile(
        r"\b(VRB|\d{3})(\d{2,3})(G(\d{2,3}))?(KT|MPS|KMH)\b"
    )
    WIND_VARIABLE_PATTERN = re.compile(r"\b(\d{3})V(\d{3})\b")
    CALM_WIND_PATTERN = re.compile(r"\b00000KT\b")

    # Visibility patterns (US and international)
    VIS_US_PATTERN = re.compile(
        r"\b(M)?(\d+)?\s*(\d/\d+)?\s*(SM)\b"
    )
    VIS_GREATER_PATTERN = re.compile(r"\bP6SM\b")
    VIS_METERS_PATTERN = re.compile(r"\b(\d{4})\b")
    CAVOK_PATTERN = re.compile(r"\bCAVOK\b")

    # Cloud patterns
    CLOUD_PATTERN = re.compile(
        r"\b(SKC|CLR|NSC|FEW|SCT|BKN|OVC|VV)(\d{3})?(CB|TCU)?\b"
    )

    # Temperature pattern
    TEMP_PATTERN = re.compile(r"\b(M)?(\d{2})/(M)?(\d{2})\b")

    # Altimeter patterns
    ALTIMETER_US_PATTERN = re.compile(r"\bA(\d{4})\b")
    ALTIMETER_INTL_PATTERN = re.compile(r"\bQ(\d{4})\b")

    # Weather phenomena pattern
    WEATHER_PATTERN = re.compile(
        r"\b([+-]|VC)?"
        r"(MI|PR|BC|DR|BL|SH|TS|FZ)?"
        r"(DZ|RA|SN|SG|IC|PL|GR|GS|UP|BR|FG|FU|VA|DU|SA|HZ|PY|PO|SQ|FC|SS|DS)+"
        r"\b"
    )

    def parse(self, raw_metar: str, source: str) -> MetarObservation:
        """Parse a raw METAR string into a MetarObservation."""
        if not raw_metar or not raw_metar.strip():
            raise MetarParseError("Empty METAR string", raw_metar)

        # Normalize the METAR string
        metar = self._normalize(raw_metar)

        # Extract ICAO code
        icao_code = self._parse_icao(metar)
        if icao_code is None:
            raise MetarParseError("Could not find valid ICAO code", raw_metar)

        # Extract observation time
        observation_time = self._parse_time(metar)
        if observation_time is None:
            raise MetarParseError("Could not parse observation time", raw_metar)

        # Extract wind data
        wind = self._parse_wind(metar)

        # Extract visibility
        visibility = self._parse_visibility(metar)

        # Extract weather phenomena
        weather = self._parse_weather(metar)

        # Extract cloud layers
        clouds = self._parse_clouds(metar)

        # Extract temperature and dewpoint
        temperature, dewpoint = self._parse_temperature(metar)

        # Extract altimeter setting
        altimeter_inhg, altimeter_hpa = self._parse_altimeter(metar)

        return MetarObservation.create(
            icao_code=icao_code,
            observation_time=observation_time,
            raw_metar=raw_metar.strip(),
            source=source,
            wind=wind,
            visibility=visibility,
            weather_phenomena=weather,
            cloud_layers=clouds,
            temperature_c=temperature,
            dewpoint_c=dewpoint,
            altimeter_inhg=altimeter_inhg,
            altimeter_hpa=altimeter_hpa,
        )

    def validate(self, raw_metar: str) -> bool:
        """Validate if a string appears to be a valid METAR."""
        if not raw_metar or not raw_metar.strip():
            return False

        metar = self._normalize(raw_metar)

        # Must have ICAO code
        if not self.ICAO_PATTERN.search(metar):
            return False

        # Must have observation time
        if not self.TIME_PATTERN.search(metar):
            return False

        return True

    def _normalize(self, metar: str) -> str:
        """Normalize METAR string for parsing."""
        # Remove METAR/SPECI prefix if present
        metar = re.sub(r"^(METAR|SPECI)\s+", "", metar.strip())
        # Collapse multiple spaces
        metar = re.sub(r"\s+", " ", metar)
        return metar.upper()

    def _parse_icao(self, metar: str) -> ICAOCode | None:
        """Extract ICAO code from METAR."""
        match = self.ICAO_PATTERN.search(metar)
        if match:
            try:
                return ICAOCode(match.group(1))
            except ValueError:
                return None
        return None

    def _parse_time(self, metar: str) -> datetime | None:
        """Extract observation time from METAR.

        Returns a UTC datetime. The day is from the METAR, and the
        month/year are inferred from the current date.
        """
        match = self.TIME_PATTERN.search(metar)
        if not match:
            return None

        day = int(match.group(1))
        hour = int(match.group(2))
        minute = int(match.group(3))

        # Get current UTC time for month/year
        now = datetime.now(timezone.utc)

        # Handle month rollover (e.g., METAR from day 31 when it's now day 1)
        try:
            observation_time = datetime(
                year=now.year,
                month=now.month,
                day=day,
                hour=hour,
                minute=minute,
                tzinfo=timezone.utc,
            )

            # If the observation time is in the future, it's probably from last month
            if observation_time > now:
                if now.month == 1:
                    observation_time = observation_time.replace(
                        year=now.year - 1, month=12
                    )
                else:
                    observation_time = observation_time.replace(month=now.month - 1)

        except ValueError:
            # Invalid day for month, try previous month
            if now.month == 1:
                try:
                    observation_time = datetime(
                        year=now.year - 1,
                        month=12,
                        day=day,
                        hour=hour,
                        minute=minute,
                        tzinfo=timezone.utc,
                    )
                except ValueError:
                    return None
            else:
                try:
                    observation_time = datetime(
                        year=now.year,
                        month=now.month - 1,
                        day=day,
                        hour=hour,
                        minute=minute,
                        tzinfo=timezone.utc,
                    )
                except ValueError:
                    return None

        return observation_time

    def _parse_wind(self, metar: str) -> Wind | None:
        """Extract wind data from METAR."""
        # Check for calm wind
        if self.CALM_WIND_PATTERN.search(metar):
            return Wind.calm()

        match = self.WIND_PATTERN.search(metar)
        if not match:
            return None

        direction_str = match.group(1)
        speed = int(match.group(2))
        gust = int(match.group(4)) if match.group(4) else None
        unit = match.group(5)

        # Convert to knots if necessary
        if unit == "MPS":
            speed = int(speed * 1.944)
            if gust:
                gust = int(gust * 1.944)
        elif unit == "KMH":
            speed = int(speed * 0.54)
            if gust:
                gust = int(gust * 0.54)

        # Check for variable wind
        is_variable = direction_str == "VRB"
        direction = None if is_variable else int(direction_str)

        # Check for variable wind direction
        var_from = None
        var_to = None
        var_match = self.WIND_VARIABLE_PATTERN.search(metar)
        if var_match:
            var_from = int(var_match.group(1))
            var_to = int(var_match.group(2))

        if is_variable:
            return Wind.variable(speed, gust)

        return Wind(
            direction_degrees=direction,
            speed_kt=speed,
            gust_kt=gust,
            variable_from=var_from,
            variable_to=var_to,
        )

    def _parse_visibility(self, metar: str) -> Visibility | None:
        """Extract visibility from METAR."""
        # Check for CAVOK
        if self.CAVOK_PATTERN.search(metar):
            return Visibility.unlimited()

        # Check for P6SM (greater than 6 statute miles)
        if self.VIS_GREATER_PATTERN.search(metar):
            return Visibility.from_statute_miles(Decimal("6"), is_greater_than=True)

        # Try US format (statute miles)
        match = self.VIS_US_PATTERN.search(metar)
        if match:
            less_than = match.group(1) is not None
            whole = int(match.group(2)) if match.group(2) else 0
            fraction_str = match.group(3)

            if fraction_str:
                num, den = fraction_str.split("/")
                fraction = Decimal(num) / Decimal(den)
            else:
                fraction = Decimal("0")

            miles = Decimal(str(whole)) + fraction

            # M prefix means less than
            return Visibility.from_statute_miles(miles, is_greater_than=not less_than)

        # Try international format (meters)
        # Look for 4-digit visibility (but not time which is 6 digits + Z)
        for match in self.VIS_METERS_PATTERN.finditer(metar):
            # Make sure it's not part of a longer number sequence
            pos = match.start()
            # Skip if it looks like a time (preceded by nothing or space, followed by Z)
            if pos > 0 and metar[pos - 1].isdigit():
                continue

            end_pos = match.end()
            if end_pos < len(metar) and metar[end_pos] == "Z":
                continue

            meters = int(match.group(1))
            if meters == 9999:
                return Visibility.from_meters(10000, is_greater_than=True)
            return Visibility.from_meters(meters)

        return None

    def _parse_weather(self, metar: str) -> list[WeatherPhenomenon]:
        """Extract weather phenomena from METAR."""
        phenomena = []

        for match in self.WEATHER_PATTERN.finditer(metar):
            try:
                wp = WeatherPhenomenon.from_code(match.group(0))
                phenomena.append(wp)
            except ValueError:
                # Skip invalid weather codes
                continue

        return phenomena

    def _parse_clouds(self, metar: str) -> list[CloudLayer]:
        """Extract cloud layers from METAR."""
        layers = []

        for match in self.CLOUD_PATTERN.finditer(metar):
            coverage_str = match.group(1)
            altitude_str = match.group(2)
            cloud_type = match.group(3)

            try:
                coverage = CloudCoverage.from_string(coverage_str)
            except ValueError:
                continue

            altitude_ft = None
            if altitude_str:
                altitude_ft = int(altitude_str) * 100  # Convert hundreds to feet

            layer = CloudLayer(
                coverage=coverage,
                altitude_ft=altitude_ft,
                cloud_type=cloud_type,
            )
            layers.append(layer)

        return layers

    def _parse_temperature(self, metar: str) -> tuple[Decimal | None, Decimal | None]:
        """Extract temperature and dewpoint from METAR."""
        match = self.TEMP_PATTERN.search(metar)
        if not match:
            return None, None

        temp_neg = match.group(1) is not None
        temp_val = int(match.group(2))
        dew_neg = match.group(3) is not None
        dew_val = int(match.group(4))

        temperature = Decimal(str(temp_val))
        if temp_neg:
            temperature = -temperature

        dewpoint = Decimal(str(dew_val))
        if dew_neg:
            dewpoint = -dewpoint

        return temperature, dewpoint

    def _parse_altimeter(self, metar: str) -> tuple[Decimal | None, int | None]:
        """Extract altimeter setting from METAR.

        Returns (altimeter_inhg, altimeter_hpa)
        """
        # US format (inches of mercury)
        us_match = self.ALTIMETER_US_PATTERN.search(metar)
        if us_match:
            try:
                inhg = Decimal(us_match.group(1)) / Decimal("100")
                # Convert to hPa
                hpa = int(inhg * Decimal("33.8639"))
                return inhg, hpa
            except (InvalidOperation, ValueError):
                pass

        # International format (hectopascals/millibars)
        intl_match = self.ALTIMETER_INTL_PATTERN.search(metar)
        if intl_match:
            try:
                hpa = int(intl_match.group(1))
                # Convert to inHg
                inhg = Decimal(str(hpa)) / Decimal("33.8639")
                inhg = inhg.quantize(Decimal("0.01"))
                return inhg, hpa
            except (InvalidOperation, ValueError):
                pass

        return None, None
