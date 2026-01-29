"""TVDB v4 API client."""

from __future__ import annotations

from datetime import date
from typing import TYPE_CHECKING, Any, cast

import httpx
from pydantic import ValidationError

from complexionist.api import (
    APIAuthError,
    APIError,
    APINotFoundError,
    APIRateLimitError,
    parse_date,
)
from complexionist.tvdb.models import TVDBEpisode, TVDBSeries, TVDBSeriesExtended

if TYPE_CHECKING:
    from complexionist.cache import Cache


class TVDBError(APIError):
    """Base exception for TVDB API errors."""

    pass


class TVDBAuthError(TVDBError, APIAuthError):
    """Authentication error (invalid API key or token)."""

    pass


class TVDBNotFoundError(TVDBError, APINotFoundError):
    """Resource not found."""

    pass


class TVDBRateLimitError(TVDBError, APIRateLimitError):
    """Rate limit exceeded."""

    def __init__(self, retry_after: int | None = None) -> None:
        super().__init__(retry_after=retry_after)


class TVDBClient:
    """Client for the TVDB v4 API.

    TVDB v4 uses a two-step authentication:
    1. POST your API key to /login
    2. Receive a Bearer token to use in subsequent requests
    """

    BASE_URL = "https://api4.thetvdb.com/v4"
    DEFAULT_TIMEOUT = 30.0

    def __init__(
        self,
        api_key: str | None = None,
        timeout: float = DEFAULT_TIMEOUT,
        cache: Cache | None = None,
    ) -> None:
        """Initialize the TVDB client.

        Args:
            api_key: TVDB API key. If not provided, reads from config.
            timeout: Request timeout in seconds.
            cache: Optional cache instance for storing API responses.
        """
        # Load from config if not provided
        if api_key is None:
            from complexionist.config import get_config

            cfg = get_config()
            api_key = cfg.tvdb.api_key

        self.api_key = api_key
        if not self.api_key:
            raise TVDBAuthError(
                "TVDB API key not provided. Configure api_key in complexionist.ini."
            )

        self._timeout = timeout
        self._cache = cache
        self._token: str | None = None
        self._client: httpx.Client | None = None

    def _get_client(self) -> httpx.Client:
        """Get or create the HTTP client with auth token."""
        if self._client is None:
            if self._token is None:
                self._login()

            self._client = httpx.Client(
                base_url=self.BASE_URL,
                timeout=self._timeout,
                headers={
                    "Accept": "application/json",
                    "Authorization": f"Bearer {self._token}",
                },
            )
        return self._client

    def login(self) -> None:
        """Authenticate and get a Bearer token.

        This is the public interface for authentication.
        Can be used to validate the API key.

        Raises:
            TVDBAuthError: If the API key is invalid.
            TVDBError: If login fails.
        """
        self._login()

    def _login(self) -> None:
        """Authenticate and get a Bearer token (internal)."""
        with httpx.Client(timeout=self._timeout) as client:
            response = client.post(
                f"{self.BASE_URL}/login",
                json={"apikey": self.api_key},
                headers={"Accept": "application/json", "Content-Type": "application/json"},
            )

            if response.status_code == 401:
                raise TVDBAuthError("Invalid TVDB API key")

            if response.status_code != 200:
                raise TVDBError(f"Login failed: {response.status_code} - {response.text}")

            data = response.json()
            self._token = data.get("data", {}).get("token")

            if not self._token:
                raise TVDBAuthError("No token received from TVDB login")

    def close(self) -> None:
        """Close the HTTP client."""
        if self._client is not None:
            self._client.close()
            self._client = None

    def __enter__(self) -> TVDBClient:
        return self

    def __exit__(self, *args: object) -> None:
        self.close()

    def _handle_response(self, response: httpx.Response) -> dict[str, Any]:
        """Handle API response and raise appropriate errors."""
        if response.status_code == 200:
            return cast(dict[str, Any], response.json())

        if response.status_code == 401:
            # Token may have expired, clear it for re-auth
            self._token = None
            self._client = None
            raise TVDBAuthError("Authentication failed - token may have expired")

        if response.status_code == 404:
            raise TVDBNotFoundError("Resource not found")

        if response.status_code == 429:
            retry_after = response.headers.get("Retry-After")
            raise TVDBRateLimitError(int(retry_after) if retry_after else None)

        # Generic error
        try:
            error_data = response.json()
            message = error_data.get("message", "Unknown error")
        except Exception:
            message = response.text or "Unknown error"

        raise TVDBError(f"TVDB API error ({response.status_code}): {message}")

    def _parse_date(self, date_str: str | None) -> date | None:
        """Parse a date string from TVDB API."""
        return parse_date(date_str)

    def get_series(self, series_id: int) -> TVDBSeries:
        """Get basic series information.

        Args:
            series_id: The TVDB series ID.

        Returns:
            Series information.
        """
        from complexionist.cache import TVDB_SERIES_TTL_HOURS
        from complexionist.statistics import ScanStatistics

        stats = ScanStatistics.get_current()
        cache_key = str(series_id)

        # Check cache first
        if self._cache:
            cached = self._cache.get("tvdb", "series", cache_key)
            if cached:
                if stats:
                    stats.record_cache_hit("tvdb")
                return TVDBSeries.model_validate(cached)

        # Cache miss - making API call
        if stats:
            stats.record_cache_miss("tvdb")
            stats.record_api_call("tvdb_series")

        client = self._get_client()
        response = client.get(f"/series/{series_id}")
        data = self._handle_response(response)

        series_data = data.get("data", {})

        try:
            series = TVDBSeries(
                id=series_data["id"],
                name=series_data["name"],
                slug=series_data.get("slug"),
                status=series_data.get("status", {}).get("name")
                if series_data.get("status")
                else None,
                firstAired=self._parse_date(series_data.get("firstAired")),
                overview=series_data.get("overview"),
                year=series_data.get("year"),
                image=series_data.get("image"),
            )

            # Store in cache
            if self._cache:
                self._cache.set(
                    "tvdb",
                    "series",
                    cache_key,
                    series.model_dump(mode="json"),
                    ttl_hours=TVDB_SERIES_TTL_HOURS,
                    description=f"Series: {series.name}",
                )

            return series
        except (ValidationError, KeyError) as e:
            raise TVDBError(f"Failed to parse series response: {e}") from e

    def get_series_episodes(
        self,
        series_id: int,
        season_type: str = "default",
    ) -> list[TVDBEpisode]:
        """Get all episodes for a series.

        This handles pagination automatically to fetch all episodes.

        Args:
            series_id: The TVDB series ID.
            season_type: Episode ordering type ("default", "official", "dvd", "absolute").

        Returns:
            List of all episodes.
        """
        from complexionist.cache import TVDB_EPISODES_TTL_HOURS
        from complexionist.statistics import ScanStatistics

        stats = ScanStatistics.get_current()

        # Build cache key including season_type
        cache_key = f"{series_id}_{season_type}"

        # Check cache first
        if self._cache:
            cached = self._cache.get("tvdb", "episodes", cache_key)
            if cached and "episodes" in cached:
                if stats:
                    stats.record_cache_hit("tvdb")
                return [TVDBEpisode.model_validate(ep) for ep in cached["episodes"]]

        # Cache miss - making API call
        if stats:
            stats.record_cache_miss("tvdb")
            stats.record_api_call("tvdb_episode")

        client = self._get_client()
        all_episodes: list[TVDBEpisode] = []
        page = 0

        while True:
            response = client.get(
                f"/series/{series_id}/episodes/{season_type}",
                params={"page": page},
            )
            data = self._handle_response(response)

            episodes_data = data.get("data", {}).get("episodes", [])
            if not episodes_data:
                break

            for ep_data in episodes_data:
                try:
                    episode = TVDBEpisode(
                        id=ep_data["id"],
                        seriesId=ep_data.get("seriesId", series_id),
                        name=ep_data.get("name"),
                        seasonNumber=ep_data.get("seasonNumber", 0),
                        number=ep_data.get("number", 0),
                        aired=self._parse_date(ep_data.get("aired")),
                        overview=ep_data.get("overview"),
                        runtime=ep_data.get("runtime"),
                    )
                    all_episodes.append(episode)
                except (ValidationError, KeyError):
                    # Skip malformed episodes but continue processing
                    continue

            # Check if there are more pages
            # TVDB returns empty episodes list when no more pages
            if len(episodes_data) < 500:  # TVDB page size is typically 500
                break

            page += 1

        # Store in cache
        if self._cache and all_episodes:
            self._cache.set(
                "tvdb",
                "episodes",
                cache_key,
                {"episodes": [ep.model_dump(mode="json") for ep in all_episodes]},
                ttl_hours=TVDB_EPISODES_TTL_HOURS,
                description=f"Series {series_id} ({len(all_episodes)} episodes)",
            )

        return all_episodes

    def get_series_with_episodes(
        self,
        series_id: int,
        season_type: str = "default",
    ) -> TVDBSeriesExtended:
        """Get series info with all episodes.

        Args:
            series_id: The TVDB series ID.
            season_type: Episode ordering type.

        Returns:
            Series with all episodes.
        """
        series = self.get_series(series_id)
        episodes = self.get_series_episodes(series_id, season_type)

        return TVDBSeriesExtended(
            id=series.id,
            name=series.name,
            slug=series.slug,
            status=series.status,
            firstAired=series.first_aired,
            overview=series.overview,
            year=series.year,
            image=series.image,
            episodes=episodes,
        )

    def search_series(self, query: str) -> list[TVDBSeries]:
        """Search for series by name.

        Args:
            query: Search query string.

        Returns:
            List of matching series.
        """
        client = self._get_client()
        response = client.get("/search", params={"query": query, "type": "series"})
        data = self._handle_response(response)

        results = []
        for item in data.get("data", []):
            try:
                series = TVDBSeries(
                    id=int(item["tvdb_id"]),
                    name=item["name"],
                    slug=item.get("slug"),
                    status=item.get("status"),
                    firstAired=self._parse_date(item.get("first_air_time")),
                    overview=item.get("overview"),
                    year=int(item["year"]) if item.get("year") else None,
                    image=item.get("image_url") or item.get("image"),
                )
                results.append(series)
            except (ValidationError, KeyError, ValueError):
                continue

        return results

    def test_connection(self) -> bool:
        """Test the API connection and key validity.

        Returns:
            True if connection is successful.

        Raises:
            TVDBAuthError: If the API key is invalid.
            TVDBError: If there's a connection error.
        """
        try:
            # Login will validate the API key
            if self._token is None:
                self._login()
            return True
        except httpx.RequestError as e:
            raise TVDBError(f"Connection error: {e}") from e
