"""Theme configuration for ComPlexionist GUI."""

import flet as ft

# Plex brand color
PLEX_GOLD = "#F7C600"

# App colors
BACKGROUND_DARK = "#1a1a2e"
SURFACE_DARK = "#16213e"
BACKGROUND_LIGHT = "#f5f5f5"
SURFACE_LIGHT = "#ffffff"


def create_theme(dark_mode: bool = True) -> ft.Theme:
    """Create the app theme with Plex gold accent.

    Args:
        dark_mode: Whether to use dark mode (default: True).

    Returns:
        Configured Flet theme.
    """
    return ft.Theme(
        color_scheme_seed=PLEX_GOLD,
        color_scheme=ft.ColorScheme(
            primary=PLEX_GOLD,
            on_primary="#000000",
            secondary=PLEX_GOLD,
        ),
    )


def get_theme_mode(dark_mode: bool = True) -> ft.ThemeMode:
    """Get the theme mode.

    Args:
        dark_mode: Whether to use dark mode.

    Returns:
        ThemeMode.DARK or ThemeMode.LIGHT.
    """
    return ft.ThemeMode.DARK if dark_mode else ft.ThemeMode.LIGHT
