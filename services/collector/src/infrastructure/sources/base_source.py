"""Base class for METAR sources with common functionality."""

from __future__ import annotations

import asyncio
from abc import abstractmethod
from typing import TYPE_CHECKING

import httpx
import structlog
from tenacity import (
    RetryError,
    retry,
    retry_if_exception_type,
    stop_after_attempt,
    wait_exponential,
)

from src.domain.interfaces import (
    IMetarSource,
    MetarSourceConnectionError,
    MetarSourceError,
    MetarSourceResult,
    MetarSourceTimeoutError,
)

if TYPE_CHECKING:
    from src.domain.value_objects import ICAOCode

logger = structlog.get_logger(__name__)


class CircuitBreaker:
    """Simple circuit breaker implementation for source resilience."""

    def __init__(
        self,
        failure_threshold: int = 5,
        recovery_timeout: float = 60.0,
    ):
        self.failure_threshold = failure_threshold
        self.recovery_timeout = recovery_timeout
        self.failures = 0
        self.last_failure_time: float | None = None
        self.is_open = False

    def record_success(self) -> None:
        """Record a successful call, resetting the failure count."""
        self.failures = 0
        self.is_open = False

    def record_failure(self) -> None:
        """Record a failed call, potentially opening the circuit."""
        self.failures += 1
        self.last_failure_time = asyncio.get_event_loop().time()
        if self.failures >= self.failure_threshold:
            self.is_open = True

    def can_proceed(self) -> bool:
        """Check if a call should be allowed."""
        if not self.is_open:
            return True

        # Check if recovery timeout has passed
        if self.last_failure_time is not None:
            elapsed = asyncio.get_event_loop().time() - self.last_failure_time
            if elapsed >= self.recovery_timeout:
                self.is_open = False
                self.failures = 0
                return True

        return False


class BaseMetarSource(IMetarSource):
    """Base class for METAR data sources.

    Provides common functionality like:
    - HTTP client management
    - Retry logic with exponential backoff
    - Circuit breaker pattern
    - Logging
    """

    def __init__(
        self,
        timeout_seconds: float = 30.0,
        retry_attempts: int = 3,
        retry_delay_seconds: float = 5.0,
    ):
        self._timeout = timeout_seconds
        self._retry_attempts = retry_attempts
        self._retry_delay = retry_delay_seconds
        self._circuit_breaker = CircuitBreaker()
        self._client: httpx.AsyncClient | None = None

    async def _get_client(self) -> httpx.AsyncClient:
        """Get or create the HTTP client."""
        if self._client is None or self._client.is_closed:
            self._client = httpx.AsyncClient(
                timeout=httpx.Timeout(self._timeout),
                follow_redirects=True,
            )
        return self._client

    async def close(self) -> None:
        """Close the HTTP client."""
        if self._client and not self._client.is_closed:
            await self._client.aclose()
            self._client = None

    async def _make_request(
        self,
        url: str,
        params: dict[str, str] | None = None,
        headers: dict[str, str] | None = None,
    ) -> httpx.Response:
        """Make an HTTP request with retry logic."""
        if not self._circuit_breaker.can_proceed():
            raise MetarSourceConnectionError(
                "Circuit breaker is open",
                source=self.name,
            )

        client = await self._get_client()

        @retry(
            retry=retry_if_exception_type((httpx.TimeoutException, httpx.ConnectError)),
            stop=stop_after_attempt(self._retry_attempts),
            wait=wait_exponential(multiplier=self._retry_delay, min=1, max=30),
            reraise=True,
        )
        async def _request() -> httpx.Response:
            return await client.get(url, params=params, headers=headers)

        try:
            response = await _request()
            self._circuit_breaker.record_success()
            return response

        except httpx.TimeoutException as e:
            self._circuit_breaker.record_failure()
            raise MetarSourceTimeoutError(
                f"Request timed out: {e}",
                source=self.name,
            ) from e

        except httpx.ConnectError as e:
            self._circuit_breaker.record_failure()
            raise MetarSourceConnectionError(
                f"Connection failed: {e}",
                source=self.name,
            ) from e

        except RetryError as e:
            self._circuit_breaker.record_failure()
            raise MetarSourceConnectionError(
                f"Max retries exceeded: {e}",
                source=self.name,
            ) from e

    @property
    @abstractmethod
    def name(self) -> str:
        """Return the name of this source."""
        ...

    @property
    @abstractmethod
    def is_available(self) -> bool:
        """Check if the source is currently available."""
        ...

    @abstractmethod
    async def fetch_metar(self, icao_code: ICAOCode | str) -> MetarSourceResult:
        """Fetch METAR for a single airport."""
        ...

    @abstractmethod
    async def fetch_metars(
        self, icao_codes: list[ICAOCode | str]
    ) -> list[MetarSourceResult]:
        """Fetch METARs for multiple airports."""
        ...

    async def health_check(self) -> bool:
        """Check if the source is healthy."""
        try:
            # Try to fetch a known airport
            result = await self.fetch_metar("KJFK")
            return result.success
        except MetarSourceError:
            return False
        except Exception:
            return False
