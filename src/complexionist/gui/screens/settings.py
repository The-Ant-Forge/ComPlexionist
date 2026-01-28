"""Settings screen for ComPlexionist GUI."""

from __future__ import annotations

from collections.abc import Callable
from typing import TYPE_CHECKING

import flet as ft

from complexionist.gui.screens.base import BaseScreen
from complexionist.gui.theme import PLEX_GOLD

if TYPE_CHECKING:
    from complexionist.gui.state import AppState


class SettingsScreen(BaseScreen):
    """Settings and configuration screen."""

    def __init__(
        self,
        page: ft.Page,
        state: AppState,
        on_back: Callable[[], None],
        on_theme_change: Callable[[bool], None],
        on_setup: Callable[[], None],
    ) -> None:
        """Initialize settings screen.

        Args:
            page: Flet page instance.
            state: Application state.
            on_back: Callback to go back.
            on_theme_change: Callback when theme changes (True = dark mode).
            on_setup: Callback to re-run setup wizard.
        """
        super().__init__(page, state)
        self.on_back = on_back
        self.on_theme_change = on_theme_change
        self.on_setup = on_setup

    def _create_section(self, title: str, controls: list[ft.Control]) -> ft.Card:
        """Create a settings section card."""
        return ft.Card(
            content=ft.Container(
                content=ft.Column(
                    [
                        ft.Text(title, size=16, weight=ft.FontWeight.BOLD),
                        ft.Divider(),
                        *controls,
                    ],
                    spacing=12,
                ),
                padding=16,
            ),
        )

    def _toggle_dark_mode(self, e: ft.ControlEvent) -> None:
        """Toggle dark mode."""
        self.state.dark_mode = e.control.value
        self.on_theme_change(self.state.dark_mode)

    def _test_connections(self, e: ft.ControlEvent) -> None:
        """Test all service connections."""
        # Reset connection status
        self.state.connection.plex_connected = False
        self.state.connection.tmdb_connected = False
        self.state.connection.tvdb_connected = False
        self.state.connection.error_message = ""

        # Test Plex
        try:
            from complexionist.plex import PlexClient

            plex = PlexClient()
            plex.connect()
            self.state.connection.plex_connected = True
            self.state.connection.plex_server_name = plex.server_name or "Plex Server"
            self.state.movie_libraries = [lib.title for lib in plex.get_movie_libraries()]
            self.state.tv_libraries = [lib.title for lib in plex.get_tv_libraries()]
        except Exception as ex:
            self.state.connection.error_message = f"Plex: {ex}"

        # Test TMDB
        try:
            from complexionist.tmdb import TMDBClient

            tmdb = TMDBClient()
            tmdb.test_connection()
            self.state.connection.tmdb_connected = True
        except Exception as ex:
            if self.state.connection.error_message:
                self.state.connection.error_message += f"; TMDB: {ex}"
            else:
                self.state.connection.error_message = f"TMDB: {ex}"

        # Test TVDB
        try:
            from complexionist.tvdb import TVDBClient

            tvdb = TVDBClient()
            tvdb.test_connection()
            self.state.connection.tvdb_connected = True
        except Exception as ex:
            if self.state.connection.error_message:
                self.state.connection.error_message += f"; TVDB: {ex}"
            else:
                self.state.connection.error_message = f"TVDB: {ex}"

        # Update UI with snackbar
        all_connected = (
            self.state.connection.plex_connected
            and self.state.connection.tmdb_connected
            and self.state.connection.tvdb_connected
        )
        self.page.snack_bar = ft.SnackBar(
            content=ft.Text(
                "All connections successful!"
                if all_connected
                else f"Connection issues: {self.state.connection.error_message}"
            ),
            bgcolor=ft.Colors.GREEN if all_connected else ft.Colors.ORANGE,
        )
        self.page.snack_bar.open = True
        self.page.update()

    def _clear_cache(self, e: ft.ControlEvent) -> None:
        """Clear the API response cache."""
        from complexionist.cache import Cache

        cache = Cache()
        count = cache.clear()

        self.page.snack_bar = ft.SnackBar(
            content=ft.Text(f"Cache cleared: {count} entries removed"),
        )
        self.page.snack_bar.open = True
        self.page.update()

    def build(self) -> ft.Control:
        """Build the settings UI."""
        # Header
        header = ft.Row(
            [
                ft.IconButton(
                    icon=ft.Icons.ARROW_BACK,
                    on_click=lambda e: self.on_back(),
                ),
                ft.Text("Settings", size=24, weight=ft.FontWeight.BOLD),
            ],
        )

        # Appearance section
        appearance = self._create_section(
            "Appearance",
            [
                ft.Row(
                    [
                        ft.Column(
                            [
                                ft.Text("Dark Mode"),
                                ft.Text(
                                    "Use dark theme for the interface",
                                    size=12,
                                    color=ft.Colors.GREY_400,
                                ),
                            ],
                            spacing=2,
                        ),
                        ft.Switch(
                            value=self.state.dark_mode,
                            on_change=self._toggle_dark_mode,
                            active_color=PLEX_GOLD,
                        ),
                    ],
                    alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
                ),
            ],
        )

        # Connection section
        connection = self._create_section(
            "Connections",
            [
                ft.ListTile(
                    leading=ft.Icon(ft.Icons.DNS),
                    title=ft.Text("Plex Server"),
                    subtitle=ft.Text(
                        self.state.connection.plex_server_name or "Not configured",
                        color=ft.Colors.GREY_400,
                    ),
                    trailing=ft.Icon(
                        ft.Icons.CHECK_CIRCLE
                        if self.state.connection.plex_connected
                        else ft.Icons.ERROR,
                        color=ft.Colors.GREEN
                        if self.state.connection.plex_connected
                        else ft.Colors.RED,
                    ),
                ),
                ft.ListTile(
                    leading=ft.Icon(ft.Icons.MOVIE),
                    title=ft.Text("TMDB"),
                    subtitle=ft.Text("Movie collection data", color=ft.Colors.GREY_400),
                    trailing=ft.Icon(
                        ft.Icons.CHECK_CIRCLE
                        if self.state.connection.tmdb_connected
                        else ft.Icons.ERROR,
                        color=ft.Colors.GREEN
                        if self.state.connection.tmdb_connected
                        else ft.Colors.RED,
                    ),
                ),
                ft.ListTile(
                    leading=ft.Icon(ft.Icons.TV),
                    title=ft.Text("TVDB"),
                    subtitle=ft.Text("TV episode data", color=ft.Colors.GREY_400),
                    trailing=ft.Icon(
                        ft.Icons.CHECK_CIRCLE
                        if self.state.connection.tvdb_connected
                        else ft.Icons.ERROR,
                        color=ft.Colors.GREEN
                        if self.state.connection.tvdb_connected
                        else ft.Colors.RED,
                    ),
                ),
                ft.Row(
                    [
                        ft.ElevatedButton(
                            "Test Connections",
                            icon=ft.Icons.REFRESH,
                            on_click=self._test_connections,
                        ),
                        ft.OutlinedButton(
                            "Run Setup",
                            icon=ft.Icons.SETTINGS_SUGGEST,
                            on_click=lambda e: self.on_setup(),
                        ),
                    ],
                    spacing=8,
                ),
            ],
        )

        # Scan options section
        scan_options = self._create_section(
            "Scan Options",
            [
                ft.Row(
                    [
                        ft.Column(
                            [
                                ft.Text("Exclude Future Releases"),
                                ft.Text(
                                    "Don't show unreleased movies/episodes",
                                    size=12,
                                    color=ft.Colors.GREY_400,
                                ),
                            ],
                            spacing=2,
                        ),
                        ft.Switch(value=True, active_color=PLEX_GOLD),
                    ],
                    alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
                ),
                ft.Row(
                    [
                        ft.Column(
                            [
                                ft.Text("Exclude Specials"),
                                ft.Text(
                                    "Don't show Season 0 episodes",
                                    size=12,
                                    color=ft.Colors.GREY_400,
                                ),
                            ],
                            spacing=2,
                        ),
                        ft.Switch(value=True, active_color=PLEX_GOLD),
                    ],
                    alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
                ),
            ],
        )

        # Cache section
        cache_section = self._create_section(
            "Cache",
            [
                ft.Row(
                    [
                        ft.Column(
                            [
                                ft.Text("API Response Cache"),
                                ft.Text(
                                    f"Location: {self.state.config_path or 'Default'}",
                                    size=12,
                                    color=ft.Colors.GREY_400,
                                ),
                            ],
                            spacing=2,
                            expand=True,
                        ),
                        ft.OutlinedButton(
                            "Clear Cache",
                            icon=ft.Icons.DELETE_SWEEP,
                            on_click=self._clear_cache,
                        ),
                    ],
                    alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
                ),
            ],
        )

        # About section
        from complexionist import __version__

        about = self._create_section(
            "About",
            [
                ft.ListTile(
                    title=ft.Text("ComPlexionist"),
                    subtitle=ft.Text(f"Version {__version__}", color=ft.Colors.GREY_400),
                ),
                ft.Row(
                    [
                        ft.TextButton(
                            "GitHub",
                            icon=ft.Icons.CODE,
                            url="https://github.com/StephKoenig/ComPlexionist",
                        ),
                        ft.TextButton(
                            "Documentation",
                            icon=ft.Icons.MENU_BOOK,
                        ),
                    ],
                    spacing=8,
                ),
            ],
        )

        return ft.Container(
            content=ft.Column(
                [
                    header,
                    ft.Divider(),
                    ft.ListView(
                        controls=[
                            appearance,
                            connection,
                            scan_options,
                            cache_section,
                            about,
                        ],
                        expand=True,
                        spacing=16,
                        padding=ft.padding.only(top=16),
                    ),
                ],
            ),
            padding=16,
            expand=True,
        )
