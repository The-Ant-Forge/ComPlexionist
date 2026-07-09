"""Shared error messages and utilities for ComPlexionist.

Provides user-friendly error message conversion and file-based error
logging used by both CLI and GUI.
"""

from __future__ import annotations

import traceback
from datetime import datetime
from pathlib import Path

# =============================================================================
# Error log file
# =============================================================================


def _get_log_file_path() -> Path:
    """Get the path to the error log file (in exe folder or cwd)."""
    from complexionist.config import get_exe_directory

    return get_exe_directory() / "complexionist_errors.log"


def log_error(error: Exception | str, context: str = "") -> None:
    """Log an error to the log file.

    When given an exception with an attached traceback, the full formatted
    traceback is appended to the entry so failures are diagnosable after
    the fact.

    Args:
        error: The error (exception or string).
        context: Optional context about where the error occurred.
    """
    try:
        log_path = _get_log_file_path()
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        tb_text = ""
        if isinstance(error, str):
            message = error
            error_type = "Message"
        else:
            message = str(error)
            error_type = type(error).__name__
            if error.__traceback__ is not None:
                tb_text = "".join(traceback.format_exception(error))

        log_entry = f"[{timestamp}] {error_type}"
        if context:
            log_entry += f" ({context})"
        log_entry += f": {message}\n"
        if tb_text:
            log_entry += tb_text

        with open(log_path, "a", encoding="utf-8") as f:
            f.write(log_entry)
    except Exception:
        # Don't let logging errors crash the app
        pass


# =============================================================================
# User-friendly error messages
# =============================================================================

ERROR_UNKNOWN = "An unexpected error occurred. Please try again."
ERROR_CONNECTION_REFUSED = "Cannot connect to the server. Is it running?"
ERROR_CONNECTION_TIMEOUT = "Connection timed out. The server may be slow or unreachable."
ERROR_PLEX_UNAUTHORIZED = "Plex authentication failed. Check your token in settings."
ERROR_PLEX_NOT_FOUND = "Plex server not found at the configured URL."
ERROR_TMDB_UNAUTHORIZED = "TMDB API key is invalid. Check your key in settings."
ERROR_TMDB_RATE_LIMIT = "TMDB rate limit reached. Please wait a moment and try again."
ERROR_TVDB_UNAUTHORIZED = "TVDB API key is invalid. Check your key in settings."
ERROR_TVDB_RATE_LIMIT = "TVDB rate limit reached. Please wait a moment and try again."
ERROR_NO_CONFIG = "No configuration found. Please run the setup wizard."


def get_friendly_message(error: Exception) -> str:
    """Convert a technical exception to a user-friendly message.

    Args:
        error: The exception that occurred.

    Returns:
        A user-friendly error message.
    """
    error_str = str(error).lower()
    error_type = type(error).__name__

    # Connection errors
    if "connection refused" in error_str or "connectrefusederror" in error_type.lower():
        return ERROR_CONNECTION_REFUSED
    if "timeout" in error_str or "timed out" in error_str:
        return ERROR_CONNECTION_TIMEOUT

    # Plex errors
    if "plexautherror" in error_type.lower() or "401" in error_str:
        if "plex" in error_str:
            return ERROR_PLEX_UNAUTHORIZED
    if "plexnotfounderror" in error_type.lower() or "plexerror" in error_type.lower():
        if "not found" in error_str:
            return ERROR_PLEX_NOT_FOUND

    # TMDB errors
    if "tmdbautherror" in error_type.lower():
        return ERROR_TMDB_UNAUTHORIZED
    if "tmdbratelimiterror" in error_type.lower():
        return ERROR_TMDB_RATE_LIMIT
    if "tmdb" in error_str and ("401" in error_str or "unauthorized" in error_str):
        return ERROR_TMDB_UNAUTHORIZED

    # TVDB errors
    if "tvdbautherror" in error_type.lower():
        return ERROR_TVDB_UNAUTHORIZED
    if "tvdbratelimiterror" in error_type.lower():
        return ERROR_TVDB_RATE_LIMIT
    if "tvdb" in error_str and ("401" in error_str or "unauthorized" in error_str):
        return ERROR_TVDB_UNAUTHORIZED

    # Config errors
    if "no configuration" in error_str or "config" in error_str and "not found" in error_str:
        return ERROR_NO_CONFIG

    # Default - return the original error message if it's already user-friendly
    # Otherwise return generic message
    if len(str(error)) < 100 and not any(
        tech in error_str for tech in ["traceback", "exception", "error:", "errno"]
    ):
        return str(error)

    return ERROR_UNKNOWN
