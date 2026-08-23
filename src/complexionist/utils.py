"""Utility functions for ComPlexionist."""

import threading
import time
from collections.abc import Callable
from datetime import date, timedelta
from functools import wraps
from typing import ParamSpec, TypeVar

P = ParamSpec("P")
T = TypeVar("T")

# Shared throttle for outbound metadata-API calls.
#
# TMDB removed its 40-requests-per-10-seconds cap in 2019 and now documents a
# soft ceiling "in the 40 requests per second range", enforced with HTTP 429.
# We deliberately run at half that: it is a per-IP budget that TMDB may change
# without notice, and it may be shared (CGNAT, VPN). Overshoot is not fatal --
# `retry_with_backoff` retries 429s and honours the server's Retry-After -- but
# repeated 429s burn retries and end in skipped items, so headroom is cheap.
API_MIN_INTERVAL = 0.05  # seconds between uncached calls -> 20 req/s
API_MAX_WORKERS = 8  # enough requests in flight to actually sustain that rate


class RateLimiter:
    """Enforce a minimum interval between calls, shared across threads.

    Workers call :meth:`wait` immediately before an uncached API request. The
    lock is held across the sleep, so concurrent workers queue rather than all
    waking at once -- the resulting rate is ``1 / min_interval`` in total, not
    per worker. Cached lookups should skip this entirely.
    """

    def __init__(self, min_interval: float = API_MIN_INTERVAL) -> None:
        self._min_interval = min_interval
        self._lock = threading.Lock()
        self._last_call = 0.0

    def wait(self) -> None:
        """Block until at least ``min_interval`` has passed since the last call."""
        with self._lock:
            elapsed = time.monotonic() - self._last_call
            if elapsed < self._min_interval:
                time.sleep(self._min_interval - elapsed)
            self._last_call = time.monotonic()


def is_date_past(d: date | None) -> bool:
    """Check if a date is at least 1 day before today.

    Adds a 24-hour grace period because content released/aired "today"
    in one timezone may not be available for download until the next day.

    Note: for TV episodes this interacts with the ``recent_threshold_hours``
    filter (see ``_filter_tvdb_episodes`` in ``gaps/episodes.py``), which
    covers the same "too recent to flag" concern. With this 24h grace in
    place, thresholds of 48 hours or less are effectively subsumed.
    """
    if d is None:
        return False
    return d < date.today() - timedelta(days=1)


def retry_with_backoff(
    max_retries: int = 3,
    base_delay: float = 1.0,
    max_delay: float = 60.0,
    exponential_base: float = 2.0,
    retry_on: tuple[type[Exception], ...] = (Exception,),
) -> Callable[[Callable[P, T]], Callable[P, T]]:
    """Decorator that retries a function with exponential backoff.

    Args:
        max_retries: Maximum number of retry attempts.
        base_delay: Initial delay in seconds.
        max_delay: Maximum delay in seconds.
        exponential_base: Base for exponential backoff.
        retry_on: Tuple of exception types to retry on.

    Returns:
        Decorated function that retries on failure.
    """

    def decorator(func: Callable[P, T]) -> Callable[P, T]:
        @wraps(func)
        def wrapper(*args: P.args, **kwargs: P.kwargs) -> T:
            last_exception: Exception | None = None

            for attempt in range(max_retries + 1):
                try:
                    return func(*args, **kwargs)
                except retry_on as e:
                    last_exception = e

                    if attempt == max_retries:
                        break

                    # Calculate delay with exponential backoff
                    delay = min(base_delay * (exponential_base**attempt), max_delay)

                    # Check if the exception has a retry_after attribute (rate limiting)
                    if hasattr(e, "retry_after") and e.retry_after:
                        delay = max(delay, e.retry_after)

                    time.sleep(delay)

            # All retries exhausted
            raise last_exception  # type: ignore[misc]

        return wrapper

    return decorator
