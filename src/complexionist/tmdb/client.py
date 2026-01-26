"""TMDB API client."""

from __future__ import annotations

from typing import TYPE_CHECKING

import httpx
from pydantic import ValidationError

from complexionist.api import (
    APIAuthError,
    APIError,
    APINotFoundError,
    APIRateLimitError,
    parse_date,
)
from complexionist.tmdb.models import TMDBCollection, TMDBMovie, TMDBMovieDetails

if TYPE_CHECKING:
    from complexionist.cache import Cache


class TMDBError(APIError):
    """Base exception for TMDB API errors."""

    pass


class TMDBAuthError(TMDBError, APIAuthError):
    """Authentication error (invalid API key)."""

    pass


class TMDBNotFoundError(TMDBError, APINotFoundError):
    """Resource not found."""

    pass


class TMDBRateLimitError(TMDBError, APIRateLimitError):
    """Rate limit exceeded."""

    def __init__(self, retry_after: int | None = None) -> None:
        super().__init__(retry_after=retry_after)


class TMDBClient:
    """Client for the TMDB API."""

    BASE_URL = "https://api.themoviedb.org/3"
    DEFAULT_TIMEOUT = 30.0

    def __init__(
        self,
        api_key: str | None = None,
        timeout: float = DEFAULT_TIMEOUT,
        cache: Cache | None = None,
    ) -> None:
        """Initialize the TMDB client.

        Args:
            api_key: TMDB API key. If not provided, reads from config.
            timeout: Request timeout in seconds.
            cache: Optional cache instance for storing API responses.
        """
        # Load from config if not provided
        if api_key is None:
            from complexionist.config import get_config

            cfg = get_config()
            api_key = cfg.tmdb.api_key

        self.api_key = api_key
        if not self.api_key:
            raise TMDBAuthError(
                "TMDB API key not provided. Configure api_key in complexionist.ini."
            )

        self._cache = cache
        self._client = httpx.Client(
            base_url=self.BASE_URL,
            timeout=timeout,
            headers={"Accept": "application/json"},
            params={"api_key": self.api_key},
        )

    def close(self) -> None:
        """Close the HTTP client."""
        self._client.close()

    def __enter__(self) -> TMDBClient:
        return self

    def __exit__(self, *args: object) -> None:
        self.close()

    def _handle_response(self, response: httpx.Response) -> dict:
        """Handle API response and raise appropriate errors."""
        if response.status_code == 200:
            return response.json()

        if response.status_code == 401:
            raise TMDBAuthError("Invalid API key")

        if response.status_code == 404:
            raise TMDBNotFoundError("Resource not found")

        if response.status_code == 429:
            retry_after = response.headers.get("Retry-After")
            raise TMDBRateLimitError(int(retry_after) if retry_after else None)

        # Generic error
        try:
            error_data = response.json()
            message = error_data.get("status_message", "Unknown error")
        except Exception:
            message = response.text or "Unknown error"

        raise TMDBError(f"TMDB API error ({response.status_code}): {message}")

    def _parse_date(self, date_str: str | None):
        """Parse a date string from TMDB API."""
        return parse_date(date_str)

    def get_movie(self, movie_id: int) -> TMDBMovieDetails:
        """Get movie details including collection membership.

        Args:
            movie_id: The TMDB movie ID.

        Returns:
            Movie details with collection info if applicable.
        """
        from complexionist.cache import (
            TMDB_MOVIE_WITH_COLLECTION_TTL_HOURS,
            TMDB_MOVIE_WITHOUT_COLLECTION_TTL_HOURS,
        )
        from complexionist.statistics import ScanStatistics

        stats = ScanStatistics.get_current()

        # Check cache first
        if self._cache:
            cached = self._cache.get("tmdb", "movies", str(movie_id))
            if cached:
                if stats:
                    stats.record_cache_hit()
                return TMDBMovieDetails.model_validate(cached)

        # Cache miss - making API call
        if stats:
            stats.record_cache_miss()
            stats.record_api_call("tmdb_movie")

        response = self._client.get(f"/movie/{movie_id}")
        data = self._handle_response(response)

        # Parse the response
        collection_data = data.get("belongs_to_collection")
        collection_info = None
        if collection_data:
            collection_info = {
                "id": collection_data["id"],
                "name": collection_data["name"],
                "poster_path": collection_data.get("poster_path"),
                "backdrop_path": collection_data.get("backdrop_path"),
            }

        try:
            result = TMDBMovieDetails(
                id=data["id"],
                title=data["title"],
                release_date=self._parse_date(data.get("release_date")),
                overview=data.get("overview", ""),
                poster_path=data.get("poster_path"),
                belongs_to_collection=collection_info,
            )

            # Store in cache with TTL based on collection membership
            # Movies with collections rarely change, so use longer TTL (30 days)
            # Movies without collections might be added to one, so use shorter TTL (7 days)
            if self._cache:
                ttl_hours = (
                    TMDB_MOVIE_WITH_COLLECTION_TTL_HOURS
                    if result.belongs_to_collection
                    else TMDB_MOVIE_WITHOUT_COLLECTION_TTL_HOURS
                )
                year = result.year or ""
                description = f"{result.title} ({year})" if year else result.title
                self._cache.set(
                    "tmdb",
                    "movies",
                    str(movie_id),
                    result.model_dump(mode="json"),
                    ttl_hours=ttl_hours,
                    description=description,
                )

            return result
        except ValidationError as e:
            raise TMDBError(f"Failed to parse movie response: {e}") from e

    def get_collection(self, collection_id: int) -> TMDBCollection:
        """Get a collection with all its movies.

        Args:
            collection_id: The TMDB collection ID.

        Returns:
            Collection with all movies.
        """
        from complexionist.cache import TMDB_COLLECTION_TTL_HOURS
        from complexionist.statistics import ScanStatistics

        stats = ScanStatistics.get_current()

        # Check cache first
        if self._cache:
            cached = self._cache.get("tmdb", "collections", str(collection_id))
            if cached:
                if stats:
                    stats.record_cache_hit()
                return TMDBCollection.model_validate(cached)

        # Cache miss - making API call
        if stats:
            stats.record_cache_miss()
            stats.record_api_call("tmdb_collection")

        response = self._client.get(f"/collection/{collection_id}")
        data = self._handle_response(response)

        # Parse movies in the collection
        movies = []
        for part in data.get("parts", []):
            movie = TMDBMovie(
                id=part["id"],
                title=part["title"],
                release_date=self._parse_date(part.get("release_date")),
                overview=part.get("overview", ""),
                poster_path=part.get("poster_path"),
            )
            movies.append(movie)

        try:
            result = TMDBCollection(
                id=data["id"],
                name=data["name"],
                overview=data.get("overview", ""),
                poster_path=data.get("poster_path"),
                backdrop_path=data.get("backdrop_path"),
                parts=movies,
            )

            # Store in cache
            if self._cache:
                self._cache.set(
                    "tmdb",
                    "collections",
                    str(collection_id),
                    result.model_dump(mode="json"),
                    ttl_hours=TMDB_COLLECTION_TTL_HOURS,
                    description=result.name,
                )

            return result
        except ValidationError as e:
            raise TMDBError(f"Failed to parse collection response: {e}") from e

    def search_collection(self, query: str) -> list[TMDBCollection]:
        """Search for collections by name.

        Args:
            query: Search query string.

        Returns:
            List of matching collections (basic info only, no parts).
        """
        response = self._client.get("/search/collection", params={"query": query})
        data = self._handle_response(response)

        collections = []
        for result in data.get("results", []):
            collection = TMDBCollection(
                id=result["id"],
                name=result["name"],
                overview=result.get("overview", ""),
                poster_path=result.get("poster_path"),
                backdrop_path=result.get("backdrop_path"),
                parts=[],  # Search results don't include parts
            )
            collections.append(collection)

        return collections

    def test_connection(self) -> bool:
        """Test the API connection and key validity.

        Returns:
            True if connection is successful.

        Raises:
            TMDBAuthError: If the API key is invalid.
            TMDBError: If there's a connection error.
        """
        try:
            # Use a simple endpoint to test
            response = self._client.get("/configuration")
            self._handle_response(response)
            return True
        except httpx.RequestError as e:
            raise TMDBError(f"Connection error: {e}") from e
