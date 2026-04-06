"""Utility functions for ComPlexionist."""

import time
from collections.abc import Callable
from datetime import date, timedelta
from functools import wraps
from typing import ParamSpec, TypeVar

P = ParamSpec("P")
T = TypeVar("T")


def is_date_past(d: date | None) -> bool:
    """Check if a date is at least 1 day before today.

    Adds a 24-hour grace period because content released/aired "today"
    in one timezone may not be available for download until the next day.
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
