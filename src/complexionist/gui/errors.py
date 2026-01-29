"""Centralized error handling for ComPlexionist GUI.

Provides user-friendly error messages and consistent error display.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

import flet as ft

from complexionist.gui.strings import (
    ERROR_CONNECTION_REFUSED,
    ERROR_CONNECTION_TIMEOUT,
    ERROR_NO_CONFIG,
    ERROR_PLEX_NOT_FOUND,
    ERROR_PLEX_UNAUTHORIZED,
    ERROR_TMDB_RATE_LIMIT,
    ERROR_TMDB_UNAUTHORIZED,
    ERROR_TVDB_RATE_LIMIT,
    ERROR_TVDB_UNAUTHORIZED,
    ERROR_UNKNOWN,
)

if TYPE_CHECKING:
    pass


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


def show_error(
    page: ft.Page,
    error: Exception | str,
    *,
    duration: int = 5000,
    show_details: bool = False,
) -> None:
    """Show a user-friendly error message as a snackbar.

    Args:
        page: The Flet page to show the error on.
        error: The error (exception or string).
        duration: How long to show the snackbar in milliseconds.
        show_details: If True, include technical details for debugging.
    """
    if isinstance(error, str):
        message = error
        details = None
    else:
        message = get_friendly_message(error)
        details = str(error) if show_details else None

    # Build snackbar content
    if details and details != message:
        content = ft.Column(
            [
                ft.Text(message),
                ft.Text(details, size=10, color=ft.Colors.GREY_400),
            ],
            spacing=4,
            tight=True,
        )
    else:
        content = ft.Text(message)

    snack = ft.SnackBar(
        content=content,
        bgcolor=ft.Colors.RED_700,
        duration=duration,
    )
    page.overlay.append(snack)
    snack.open = True
    page.update()


def show_warning(
    page: ft.Page,
    message: str,
    *,
    duration: int = 4000,
) -> None:
    """Show a warning message as a snackbar.

    Args:
        page: The Flet page to show the warning on.
        message: The warning message.
        duration: How long to show the snackbar in milliseconds.
    """
    snack = ft.SnackBar(
        content=ft.Text(message),
        bgcolor=ft.Colors.ORANGE_700,
        duration=duration,
    )
    page.overlay.append(snack)
    snack.open = True
    page.update()


def show_success(
    page: ft.Page,
    message: str,
    *,
    duration: int = 3000,
) -> None:
    """Show a success message as a snackbar.

    Args:
        page: The Flet page to show the message on.
        message: The success message.
        duration: How long to show the snackbar in milliseconds.
    """
    snack = ft.SnackBar(
        content=ft.Text(message),
        bgcolor=ft.Colors.GREEN_700,
        duration=duration,
    )
    page.overlay.append(snack)
    snack.open = True
    page.update()


def show_info(
    page: ft.Page,
    message: str,
    *,
    duration: int = 3000,
) -> None:
    """Show an info message as a snackbar.

    Args:
        page: The Flet page to show the message on.
        message: The info message.
        duration: How long to show the snackbar in milliseconds.
    """
    snack = ft.SnackBar(
        content=ft.Text(message),
        bgcolor=ft.Colors.BLUE_700,
        duration=duration,
    )
    page.overlay.append(snack)
    snack.open = True
    page.update()
