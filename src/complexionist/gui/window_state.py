"""Window state persistence for ComPlexionist GUI.

Saves and restores window size and position to the INI config file.
"""

from __future__ import annotations

import configparser
from dataclasses import dataclass
from pathlib import Path
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    import flet as ft


@dataclass
class WindowState:
    """Window position and size state."""

    width: int = 1000
    height: int = 700
    x: int | None = None  # None = centered
    y: int | None = None  # None = centered
    maximized: bool = False

    # Default constraints
    MIN_WIDTH: int = 800
    MIN_HEIGHT: int = 600


def _get_config_path() -> Path | None:
    """Get the path to the config file if it exists."""
    from complexionist.config import find_config_file

    return find_config_file()


def load_window_state() -> WindowState:
    """Load window state from the INI config file.

    Returns:
        WindowState with saved values or defaults.
    """
    config_path = _get_config_path()
    if config_path is None or not config_path.exists():
        return WindowState()

    try:
        parser = configparser.ConfigParser()
        parser.read(config_path, encoding="utf-8")

        if "window" not in parser:
            return WindowState()

        section = parser["window"]
        return WindowState(
            width=section.getint("width", WindowState.MIN_WIDTH),
            height=section.getint("height", WindowState.MIN_HEIGHT),
            x=section.getint("x") if "x" in section else None,
            y=section.getint("y") if "y" in section else None,
            maximized=section.getboolean("maximized", False),
        )
    except Exception:
        # If anything goes wrong, return defaults
        return WindowState()


def save_window_state(state: WindowState) -> bool:
    """Save window state to the INI config file.

    Args:
        state: The window state to save.

    Returns:
        True if saved successfully, False otherwise.
    """
    config_path = _get_config_path()
    if config_path is None or not config_path.exists():
        # Don't create a config just for window state
        return False

    try:
        parser = configparser.ConfigParser()
        parser.read(config_path, encoding="utf-8")

        # Create or update window section
        if "window" not in parser:
            parser["window"] = {}

        parser["window"]["width"] = str(state.width)
        parser["window"]["height"] = str(state.height)
        if state.x is not None:
            parser["window"]["x"] = str(state.x)
        elif "x" in parser["window"]:
            del parser["window"]["x"]
        if state.y is not None:
            parser["window"]["y"] = str(state.y)
        elif "y" in parser["window"]:
            del parser["window"]["y"]
        parser["window"]["maximized"] = str(state.maximized).lower()

        with open(config_path, "w", encoding="utf-8") as f:
            parser.write(f)

        return True
    except Exception:
        return False


def validate_window_position(
    state: WindowState,
    screen_width: int,
    screen_height: int,
) -> WindowState:
    """Validate and adjust window position to ensure it's visible.

    Args:
        state: The window state to validate.
        screen_width: Available screen width.
        screen_height: Available screen height.

    Returns:
        Adjusted WindowState that's guaranteed to be visible.
    """
    # Ensure minimum dimensions
    width = max(state.width, WindowState.MIN_WIDTH)
    height = max(state.height, WindowState.MIN_HEIGHT)

    # Don't exceed screen size
    width = min(width, screen_width)
    height = min(height, screen_height)

    # Validate position
    x = state.x
    y = state.y

    if x is not None:
        # Ensure at least 100px of window is visible horizontally
        if x < -width + 100:
            x = 0
        elif x > screen_width - 100:
            x = screen_width - width

    if y is not None:
        # Ensure at least 50px of window is visible vertically (for title bar)
        if y < 0:
            y = 0
        elif y > screen_height - 50:
            y = screen_height - height

    return WindowState(
        width=width,
        height=height,
        x=x,
        y=y,
        maximized=state.maximized,
    )


def apply_window_state(page: ft.Page, state: WindowState) -> None:
    """Apply window state to a Flet page.

    Args:
        page: The Flet page to configure.
        state: The window state to apply.
    """
    page.window.width = state.width
    page.window.height = state.height

    if state.x is not None:
        page.window.left = state.x
    if state.y is not None:
        page.window.top = state.y

    if state.maximized:
        page.window.maximized = True


def capture_window_state(page: ft.Page) -> WindowState:
    """Capture current window state from a Flet page.

    Args:
        page: The Flet page to capture state from.

    Returns:
        Current WindowState.
    """
    return WindowState(
        width=int(page.window.width or 1000),
        height=int(page.window.height or 700),
        x=int(page.window.left) if page.window.left else None,
        y=int(page.window.top) if page.window.top else None,
        maximized=bool(page.window.maximized),
    )
