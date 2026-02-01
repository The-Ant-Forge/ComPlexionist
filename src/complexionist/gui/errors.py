"""Centralized error handling for ComPlexionist GUI.

Provides user-friendly error display using shared error utilities.
"""

from __future__ import annotations

import sys
from datetime import datetime
from pathlib import Path

import flet as ft

# Import shared error message function
from complexionist.errors import get_friendly_message


def _get_log_file_path() -> Path:
    """Get the path to the error log file (in exe folder or cwd)."""
    if getattr(sys, "frozen", False):
        # Running as bundled exe - log in same folder as exe
        return Path(sys.executable).parent / "complexionist_errors.log"
    else:
        # Running in development - log in current working directory
        return Path.cwd() / "complexionist_errors.log"


def log_error(error: Exception | str, context: str = "") -> None:
    """Log an error to the log file.

    Args:
        error: The error (exception or string).
        context: Optional context about where the error occurred.
    """
    try:
        log_path = _get_log_file_path()
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        if isinstance(error, str):
            message = error
            error_type = "Message"
        else:
            message = str(error)
            error_type = type(error).__name__

        log_entry = f"[{timestamp}] {error_type}"
        if context:
            log_entry += f" ({context})"
        log_entry += f": {message}\n"

        with open(log_path, "a", encoding="utf-8") as f:
            f.write(log_entry)
    except Exception:
        # Don't let logging errors crash the app
        pass


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
