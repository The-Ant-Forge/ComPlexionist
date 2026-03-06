"""Base classes for API clients.

Provides a unified exception hierarchy and base client class that both
TMDB and TVDB clients inherit from.
"""

from __future__ import annotations

from datetime import date
from typing import TYPE_CHECKING, Any, Self, cast

import httpx

from complexionist.api.helpers import parse_date

if TYPE_CHECKING:
    from complexionist.cache import Cache


class APIError(Exception):
    """Base exception for all API errors.

    This is the root class for API-related exceptions. Both TMDB and TVDB
    errors inherit from their respective bases (TMDBError, TVDBError) which
    both inherit from this class.
    """

    pass


class APIAuthError(APIError):
    """Authentication error (invalid API key or token)."""

    pass


class APINotFoundError(APIError):
    """Resource not found (404)."""

    pass


class APIRateLimitError(APIError):
    """Rate limit exceeded (429).

    Attributes:
        retry_after: Suggested wait time in seconds before retrying.
    """

    def __init__(self, retry_after: int | None = None, message: str | None = None) -> None:
        self.retry_after = retry_after
        if message is None:
            message = f"Rate limit exceeded. Retry after {retry_after}s"
        super().__init__(message)


class BaseAPIClient:
    """Base class for API clients with shared cache and HTTP patterns.

    Subclasses must set:
        - _error_cls: The base error class for this API (e.g., TMDBError)
        - _auth_error_cls: Auth error class (e.g., TMDBAuthError)
        - _not_found_cls: Not-found error class (e.g., TMDBNotFoundError)
        - _rate_limit_cls: Rate-limit error class (e.g., TMDBRateLimitError)
        - _error_message_key: JSON key for error message (e.g., "status_message")
        - _api_name: Human name for error messages (e.g., "TMDB")
    """

    _error_cls: type[APIError] = APIError
    _auth_error_cls: type[APIAuthError] = APIAuthError
    _not_found_cls: type[APINotFoundError] = APINotFoundError
    _rate_limit_cls: type[APIRateLimitError] = APIRateLimitError
    _error_message_key: str = "message"
    _api_name: str = "API"

    # Override in subclasses: config section name for API key lookup (e.g., "tmdb")
    _config_section: str = ""

    def __init__(self, cache: Cache | None = None) -> None:
        self._cache = cache
        self._client: httpx.Client | None = None

    def _resolve_api_key(self, api_key: str | None) -> str:
        """Load API key from config if not provided, validate it.

        Raises the subclass auth error if the key is missing.
        """
        if api_key is None and self._config_section:
            from complexionist.config import get_config

            cfg = get_config()
            api_key = getattr(getattr(cfg, self._config_section), "api_key", None)

        if not api_key:
            raise self._auth_error_cls(
                f"{self._api_name} API key not provided. Configure api_key in complexionist.ini."
            )
        return api_key

    @property
    def client(self) -> httpx.Client:
        """Return the active HTTP client, raising if not connected."""
        if self._client is None:
            msg = f"{self._api_name} client is not connected. Use as context manager."
            raise RuntimeError(msg)
        return self._client

    def _parse_date(self, date_str: str | None) -> date | None:
        """Parse an ISO-format date string."""
        return parse_date(date_str)

    def close(self) -> None:
        """Close the HTTP client."""
        if self._client is not None:
            self._client.close()
            self._client = None

    def __enter__(self) -> Self:
        return self

    def __exit__(self, *args: object) -> None:
        self.close()

    def _handle_response(self, response: httpx.Response) -> dict[str, Any]:
        """Handle API response and raise appropriate errors."""
        if response.status_code == 200:
            return cast(dict[str, Any], response.json())

        if response.status_code == 401:
            self._on_auth_failure()
            raise self._auth_error_cls("Authentication failed")

        if response.status_code == 404:
            raise self._not_found_cls("Resource not found")

        if response.status_code == 429:
            retry_after = response.headers.get("Retry-After")
            raise self._rate_limit_cls(int(retry_after) if retry_after else None)

        # Generic error
        try:
            error_data = response.json()
            message = error_data.get(self._error_message_key, "Unknown error")
        except Exception:
            message = response.text or f"HTTP {response.status_code}"

        raise self._error_cls(f"{self._api_name} API error ({response.status_code}): {message}")

    def _on_auth_failure(self) -> None:
        """Hook called on 401 response. Override to clear tokens etc."""

    def _record_cache_hit(self, namespace: str) -> None:
        """Record a cache hit in scan statistics."""
        from complexionist.statistics import ScanStatistics

        stats = ScanStatistics.get_current()
        if stats:
            stats.record_cache_hit(namespace)

    def _record_cache_miss(self, namespace: str, api_call_type: str) -> None:
        """Record a cache miss and API call in scan statistics."""
        from complexionist.statistics import ScanStatistics

        stats = ScanStatistics.get_current()
        if stats:
            stats.record_cache_miss(namespace)
            stats.record_api_call(api_call_type)
