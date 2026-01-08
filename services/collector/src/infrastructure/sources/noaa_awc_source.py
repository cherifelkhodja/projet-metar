"""NOAA Aviation Weather Center METAR source implementation."""

from __future__ import annotations

from typing import TYPE_CHECKING

import structlog

from src.domain.interfaces import MetarSourceError, MetarSourceResult

from .base_source import BaseMetarSource

if TYPE_CHECKING:
    from src.domain.value_objects import ICAOCode

logger = structlog.get_logger(__name__)


class NOAAAwcSource(BaseMetarSource):
    """NOAA Aviation Weather Center METAR data source.

    Uses the AWC Text Data Server API:
    https://aviationweather.gov/data/api/

    This is a free, reliable source for METAR data worldwide.
    """

    def __init__(
        self,
        base_url: str = "https://aviationweather.gov/api/data/metar",
        timeout_seconds: float = 30.0,
        retry_attempts: int = 3,
        retry_delay_seconds: float = 5.0,
    ):
        super().__init__(timeout_seconds, retry_attempts, retry_delay_seconds)
        self._base_url = base_url

    @property
    def name(self) -> str:
        """Return the source name."""
        return "noaa_awc"

    @property
    def is_available(self) -> bool:
        """NOAA AWC is always available (no API key required)."""
        return True

    async def fetch_metar(self, icao_code: ICAOCode | str) -> MetarSourceResult:
        """Fetch METAR for a single airport."""
        icao = str(icao_code).upper()

        try:
            response = await self._make_request(
                self._base_url,
                params={
                    "ids": icao,
                    "format": "raw",
                    "taf": "false",
                    "hours": "1",
                },
            )

            if response.status_code != 200:
                return MetarSourceResult.failure_result(
                    icao,
                    f"HTTP {response.status_code}: {response.text[:200]}",
                )

            raw_metar = response.text.strip()

            if not raw_metar or raw_metar.lower() == "no data found":
                return MetarSourceResult.failure_result(
                    icao,
                    "No METAR data available",
                )

            # AWC may return multiple METARs, take the most recent (first line)
            lines = raw_metar.split("\n")
            latest_metar = lines[0].strip()

            if not latest_metar:
                return MetarSourceResult.failure_result(
                    icao,
                    "Empty METAR response",
                )

            logger.debug("Fetched METAR", icao=icao, metar=latest_metar, source=self.name)
            return MetarSourceResult.success_result(icao, latest_metar)

        except MetarSourceError:
            raise
        except Exception as e:
            logger.error("Unexpected error fetching METAR", icao=icao, error=str(e))
            return MetarSourceResult.failure_result(icao, f"Unexpected error: {e}")

    async def fetch_metars(
        self, icao_codes: list[ICAOCode | str]
    ) -> list[MetarSourceResult]:
        """Fetch METARs for multiple airports in a single request.

        AWC API supports comma-separated station IDs for batch requests.
        """
        if not icao_codes:
            return []

        icao_list = [str(code).upper() for code in icao_codes]
        icao_string = ",".join(icao_list)

        results: list[MetarSourceResult] = []

        try:
            response = await self._make_request(
                self._base_url,
                params={
                    "ids": icao_string,
                    "format": "raw",
                    "taf": "false",
                    "hours": "1",
                },
            )

            if response.status_code != 200:
                # Return failure for all airports
                error_msg = f"HTTP {response.status_code}"
                return [
                    MetarSourceResult.failure_result(icao, error_msg)
                    for icao in icao_list
                ]

            raw_response = response.text.strip()

            if not raw_response or raw_response.lower() == "no data found":
                return [
                    MetarSourceResult.failure_result(icao, "No METAR data available")
                    for icao in icao_list
                ]

            # Parse the response - each line is a METAR for one airport
            metar_lines = [line.strip() for line in raw_response.split("\n") if line.strip()]

            # Build a mapping from ICAO to METAR
            metar_map: dict[str, str] = {}
            for line in metar_lines:
                # METAR format starts with ICAO code
                parts = line.split()
                if parts:
                    line_icao = parts[0].upper()
                    if len(line_icao) == 4 and line_icao.isalpha():
                        metar_map[line_icao] = line

            # Build results for each requested airport
            for icao in icao_list:
                if icao in metar_map:
                    results.append(MetarSourceResult.success_result(icao, metar_map[icao]))
                    logger.debug("Fetched METAR", icao=icao, source=self.name)
                else:
                    results.append(
                        MetarSourceResult.failure_result(icao, "No METAR in response")
                    )
                    logger.debug("No METAR found", icao=icao, source=self.name)

            return results

        except MetarSourceError:
            raise
        except Exception as e:
            logger.error("Unexpected error fetching METARs", error=str(e))
            return [
                MetarSourceResult.failure_result(icao, f"Unexpected error: {e}")
                for icao in icao_list
            ]
