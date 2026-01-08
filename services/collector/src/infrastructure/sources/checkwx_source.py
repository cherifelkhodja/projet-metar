"""CheckWX METAR source implementation."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

import structlog

from src.domain.interfaces import MetarSourceError, MetarSourceResult

from .base_source import BaseMetarSource

if TYPE_CHECKING:
    from src.domain.value_objects import ICAOCode

logger = structlog.get_logger(__name__)


class CheckWXSource(BaseMetarSource):
    """CheckWX METAR data source.

    Uses the CheckWX API:
    https://www.checkwx.com/api

    Requires a free API key for access.
    """

    def __init__(
        self,
        api_key: str | None = None,
        base_url: str = "https://api.checkwx.com/metar",
        timeout_seconds: float = 30.0,
        retry_attempts: int = 3,
        retry_delay_seconds: float = 5.0,
    ):
        super().__init__(timeout_seconds, retry_attempts, retry_delay_seconds)
        self._api_key = api_key
        self._base_url = base_url

    @property
    def name(self) -> str:
        """Return the source name."""
        return "checkwx"

    @property
    def is_available(self) -> bool:
        """Check if API key is configured."""
        return bool(self._api_key)

    def _get_headers(self) -> dict[str, str]:
        """Get API headers with authentication."""
        return {
            "X-API-Key": self._api_key or "",
            "Accept": "application/json",
        }

    async def fetch_metar(self, icao_code: ICAOCode | str) -> MetarSourceResult:
        """Fetch METAR for a single airport."""
        if not self.is_available:
            return MetarSourceResult.failure_result(
                str(icao_code),
                "CheckWX API key not configured",
            )

        icao = str(icao_code).upper()

        try:
            response = await self._make_request(
                f"{self._base_url}/{icao}",
                headers=self._get_headers(),
            )

            if response.status_code == 401:
                return MetarSourceResult.failure_result(icao, "Invalid API key")

            if response.status_code == 429:
                return MetarSourceResult.failure_result(icao, "Rate limit exceeded")

            if response.status_code != 200:
                return MetarSourceResult.failure_result(
                    icao,
                    f"HTTP {response.status_code}: {response.text[:200]}",
                )

            data = response.json()
            return self._parse_response(icao, data)

        except MetarSourceError:
            raise
        except Exception as e:
            logger.error("Unexpected error fetching METAR", icao=icao, error=str(e))
            return MetarSourceResult.failure_result(icao, f"Unexpected error: {e}")

    async def fetch_metars(
        self, icao_codes: list[ICAOCode | str]
    ) -> list[MetarSourceResult]:
        """Fetch METARs for multiple airports.

        CheckWX supports batch requests with comma-separated IDs.
        """
        if not icao_codes:
            return []

        if not self.is_available:
            return [
                MetarSourceResult.failure_result(
                    str(code),
                    "CheckWX API key not configured",
                )
                for code in icao_codes
            ]

        icao_list = [str(code).upper() for code in icao_codes]

        # CheckWX limits batch requests, process in chunks of 20
        chunk_size = 20
        results: list[MetarSourceResult] = []

        for i in range(0, len(icao_list), chunk_size):
            chunk = icao_list[i : i + chunk_size]
            chunk_results = await self._fetch_chunk(chunk)
            results.extend(chunk_results)

        return results

    async def _fetch_chunk(self, icao_list: list[str]) -> list[MetarSourceResult]:
        """Fetch METARs for a chunk of airports."""
        icao_string = ",".join(icao_list)

        try:
            response = await self._make_request(
                f"{self._base_url}/{icao_string}",
                headers=self._get_headers(),
            )

            if response.status_code == 401:
                return [
                    MetarSourceResult.failure_result(icao, "Invalid API key")
                    for icao in icao_list
                ]

            if response.status_code == 429:
                return [
                    MetarSourceResult.failure_result(icao, "Rate limit exceeded")
                    for icao in icao_list
                ]

            if response.status_code != 200:
                error_msg = f"HTTP {response.status_code}"
                return [
                    MetarSourceResult.failure_result(icao, error_msg)
                    for icao in icao_list
                ]

            data = response.json()
            return self._parse_batch_response(icao_list, data)

        except MetarSourceError:
            raise
        except Exception as e:
            logger.error("Unexpected error fetching METARs", error=str(e))
            return [
                MetarSourceResult.failure_result(icao, f"Unexpected error: {e}")
                for icao in icao_list
            ]

    def _parse_response(self, icao: str, data: dict[str, Any]) -> MetarSourceResult:
        """Parse single METAR response from CheckWX."""
        try:
            results_count = data.get("results", 0)
            if results_count == 0:
                return MetarSourceResult.failure_result(icao, "No METAR data available")

            metar_data = data.get("data", [])
            if not metar_data:
                return MetarSourceResult.failure_result(icao, "Empty response data")

            # CheckWX returns raw METAR in the data array
            raw_metar = metar_data[0] if isinstance(metar_data[0], str) else None

            if not raw_metar:
                return MetarSourceResult.failure_result(icao, "Invalid response format")

            logger.debug("Fetched METAR", icao=icao, metar=raw_metar, source=self.name)
            return MetarSourceResult.success_result(icao, raw_metar)

        except (KeyError, IndexError) as e:
            return MetarSourceResult.failure_result(icao, f"Parse error: {e}")

    def _parse_batch_response(
        self, icao_list: list[str], data: dict[str, Any]
    ) -> list[MetarSourceResult]:
        """Parse batch METAR response from CheckWX."""
        results: list[MetarSourceResult] = []
        metar_data = data.get("data", [])

        # Build a map of ICAO -> METAR
        metar_map: dict[str, str] = {}
        for item in metar_data:
            if isinstance(item, str):
                # Raw METAR string, extract ICAO from beginning
                parts = item.split()
                if parts and len(parts[0]) == 4:
                    metar_map[parts[0].upper()] = item

        # Build results for each requested airport
        for icao in icao_list:
            if icao in metar_map:
                results.append(MetarSourceResult.success_result(icao, metar_map[icao]))
                logger.debug("Fetched METAR", icao=icao, source=self.name)
            else:
                results.append(
                    MetarSourceResult.failure_result(icao, "No METAR in response")
                )

        return results
