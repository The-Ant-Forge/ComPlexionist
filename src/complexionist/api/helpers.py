"""Helper functions for API clients.

Provides reusable utilities like date parsing and cached API call pattern.
"""

from __future__ import annotations

from collections.abc import Callable
from datetime import date
from typing import TYPE_CHECKING, TypeVar

if TYPE_CHECKING:
    from complexionist.cache import Cache

T = TypeVar("T")


def parse_date(date_str: str | None) -> date | None:
    """Parse an ISO-format date string.

    Args:
        date_str: Date string in ISO format (YYYY-MM-DD) or None.

    Returns:
        Parsed date object, or None if the string is empty/invalid.
    """
    if not date_str:
        return None
    try:
        return date.fromisoformat(date_str)
    except ValueError:
        return None


def cached_api_call(
    cache: Cache | None,
    namespace: str,
    category: str,
    key: str,
    api_call_type: str,
    ttl_hours: int,
    fetch_fn: Callable[[], T],
    parse_fn: Callable[[dict], T],
    serialize_fn: Callable[[T], dict],
    description_fn: Callable[[T], str] | None = None,
) -> T:
    """Execute an API call with cache check/store pattern.

    This helper encapsulates the common pattern of:
    1. Check cache for existing data
    2. If hit, record stats and return cached result
    3. If miss, make API call and parse response
    4. Store result in cache
    5. Return result

    Args:
        cache: Cache instance (or None if caching disabled).
        namespace: Cache namespace (e.g., "tmdb", "tvdb").
        category: Cache category (e.g., "movies", "episodes").
        key: Cache key (e.g., movie ID as string).
        api_call_type: Stats tracking type (e.g., "tmdb_movie").
        ttl_hours: Cache TTL in hours.
        fetch_fn: Function that makes the API call and returns raw dict.
        parse_fn: Function that parses raw dict into model (for cached data).
        serialize_fn: Function that serializes model to dict for caching.
        description_fn: Optional function to generate cache description from result.

    Returns:
        The parsed/cached result of type T.

    Example:
        ```python
        result = cached_api_call(
            cache=self._cache,
            namespace="tmdb",
            category="movies",
            key=str(movie_id),
            api_call_type="tmdb_movie",
            ttl_hours=720,  # 30 days
            fetch_fn=lambda: self._client.get(f"/movie/{movie_id}"),
            parse_fn=TMDBMovieDetails.model_validate,
            serialize_fn=lambda r: r.model_dump(mode="json"),
            description_fn=lambda r: f"{r.title} ({r.year})" if r.year else r.title,
        )
        ```
    """
    from complexionist.statistics import ScanStatistics

    stats = ScanStatistics.get_current()

    # Check cache first
    if cache:
        cached = cache.get(namespace, category, key)
        if cached:
            if stats:
                stats.record_cache_hit(namespace)
            return parse_fn(cached)

    # Cache miss - make API call
    if stats:
        stats.record_cache_miss(namespace)
        stats.record_api_call(api_call_type)

    result = fetch_fn()

    # Store in cache
    if cache:
        description = description_fn(result) if description_fn else ""
        cache.set(
            namespace,
            category,
            key,
            serialize_fn(result),
            ttl_hours=ttl_hours,
            description=description,
        )

    return result
