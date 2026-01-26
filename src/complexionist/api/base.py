"""Base exception classes for API clients.

Provides a unified exception hierarchy that both TMDB and TVDB
clients can inherit from while still providing API-specific exceptions.
"""

from __future__ import annotations


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
