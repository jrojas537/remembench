"""
Remembench — Base Adapter Interface

Every external data source implements this contract to produce
normalized ImpactEvent objects. The base class provides:
- Shared HTTP client with connection pooling (lazily initialized)
- Automatic retry on transient failures (timeouts, 5xx)
- Consistent logging interface
- Score clamping helpers
"""

from abc import ABC, abstractmethod
from datetime import datetime

import httpx
from tenacity import (
    retry,
    stop_after_attempt,
    wait_exponential,
    retry_if_exception_type,
)

from app.logging import get_logger
from app.schemas import ImpactEventCreate


class BaseAdapter(ABC):
    """
    Abstract base class for all source adapters.

    Subclasses must implement fetch_events() to pull data from their
    specific source and normalize it into ImpactEventCreate objects.
    """

    def __init__(self, name: str) -> None:
        self.name = name
        self.logger = get_logger(f"adapter.{name}")
        self.requires_llm_classification: bool = False

    async def _get_client(self) -> httpx.AsyncClient:
        """Get the global reusable async HTTP client tied to the FastAPI application state."""
        from app.main import app
        
        # In testing contexts or isolated chron boundaries, app.state might not be booted.
        # Fallback to a local client if the global one doesn't exist on state.
        if not hasattr(app.state, "http_client"):
            app.state.http_client = httpx.AsyncClient(
                limits=httpx.Limits(max_connections=50, max_keepalive_connections=15),
                timeout=httpx.Timeout(30.0, read=60.0)
            )
            
        return app.state.http_client

    async def close(self) -> None:
        """The client is managed globally; no local cleanup required natively."""
        pass

    @abstractmethod
    async def fetch_events(
        self,
        start_date: datetime,
        end_date: datetime,
        industry: str = "wireless_retail",
        latitude: float | None = None,
        longitude: float | None = None,
        geo_label: str | None = None,
    ) -> list[ImpactEventCreate]:
        """
        Fetch and normalize events from this source.

        Args:
            start_date: Start of the date range
            end_date: End of the date range
            industry: Industry vertical key (adapters may customize queries)
            latitude: Optional lat for geo-specific queries
            longitude: Optional lng for geo-specific queries
            geo_label: Human-readable market name

        Returns:
            List of normalized ImpactEventCreate objects ready for DB insertion.
        """
        ...

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=2, max=30),
        retry=retry_if_exception_type(
            (httpx.TimeoutException, httpx.HTTPStatusError)
        ),
        reraise=True,
    )
    async def _http_get(
        self,
        url: str,
        params: dict | None = None,
        headers: dict | None = None,
        timeout: float = 30.0,
    ) -> dict | list | str:
        """
        Make a resilient HTTP GET with automatic retry.

        Retries up to 3 times with exponential backoff (2s → 4s → 8s)
        on timeouts and 5xx errors. Other errors propagate immediately.
        """
        self.logger.debug("http_request", url=url, params=params)
        client = await self._get_client()
        
        # Override the global timeout uniquely for this particular request
        response = await client.get(url, params=params, headers=headers, timeout=timeout)
        response.raise_for_status()

        content_type = response.headers.get("content-type", "")
        if "json" in content_type:
            return response.json()
        return response.text

    @staticmethod
    def _clamp_severity(value: float) -> float:
        """Clamp severity score to [0.0, 1.0] range."""
        return max(0.0, min(1.0, value))

    @staticmethod
    def _clamp_confidence(value: float) -> float:
        """Clamp confidence score to [0.0, 1.0] range."""
        return max(0.0, min(1.0, value))
