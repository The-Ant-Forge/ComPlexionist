"""Centralized error handling for ComPlexionist GUI.

Provides user-friendly error display using shared error utilities.
"""

from __future__ import annotations

import flet as ft

# Shared error utilities live in the core module (no Flet dependency);
# log_error is re-exported here for backwards compatibility.
from complexionist.errors import get_friendly_message, log_error

__all__ = [
    "log_error",
    "show_error",
    "show_info",
    "show_snackbar",
    "show_success",
    "show_warning",
]


def show_snackbar(page: ft.Page, snack: ft.SnackBar) -> None:
    """Show a snackbar and remove it from ``page.overlay`` once dismissed.

    Snackbars were previously appended to the overlay and never removed, so
    the overlay grew unboundedly over a session (review 2026-07 finding 40).

    Args:
        page: The Flet page to show the snackbar on.
        snack: The snackbar to show.
    """

    def _remove() -> None:
        if snack in page.overlay:
            page.overlay.remove(snack)
            page.update()

    snack.on_dismiss = _remove
    page.overlay.append(snack)
    snack.open = True
    page.update()


def show_error(
    page: ft.Page,
    error: Exception | str,
    *,
    persistent: bool = True,
    show_details: bool = False,
    context: str = "",
) -> None:
    """Show a user-friendly error message as a snackbar and log to file.

    Args:
        page: The Flet page to show the error on.
        error: The error (exception or string).
        persistent: If True, snackbar stays until dismissed (default for errors).
        show_details: If True, include technical details for debugging.
        context: Optional context for logging (e.g., "TVDB API scan").
    """
    # Log to file first
    log_error(error, context)

    if isinstance(error, str):
        message = error
        details = None
    else:
        message = get_friendly_message(error)
        details = str(error) if show_details else None

    # Build snackbar content with dismiss button for persistent errors
    if details and details != message:
        text_content = ft.Column(
            [
                ft.Text(message),
                ft.Text(details, size=10, color=ft.Colors.GREY_400),
            ],
            spacing=4,
            tight=True,
        )
    else:
        text_content = ft.Text(message)

    # Create snackbar - persistent errors need action to dismiss
    snack = ft.SnackBar(
        content=text_content,
        bgcolor=ft.Colors.RED_700,
        duration=None if persistent else 5000,  # None = stays until dismissed
        action="Dismiss" if persistent else None,
    )
    show_snackbar(page, snack)


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
    show_snackbar(page, snack)


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
    show_snackbar(page, snack)


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
    show_snackbar(page, snack)
