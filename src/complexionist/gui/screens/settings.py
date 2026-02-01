"""Settings screen for ComPlexionist GUI."""

from __future__ import annotations

from collections.abc import Callable
from typing import TYPE_CHECKING

import flet as ft

from complexionist.cache import get_cache_file_path
from complexionist.config import (
    get_config,
    get_config_path,
    remove_ignored_collection,
    remove_ignored_show,
    reset_config,
)
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

        # References for dynamic status updates
        self.plex_status_icon: ft.Icon | None = None
        self.tmdb_status_icon: ft.Icon | None = None
        self.tvdb_status_icon: ft.Icon | None = None
        self.plex_subtitle: ft.Text | None = None

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

        # Update status icons dynamically
        self._update_status_icons()

        # Update UI with snackbar
        all_connected = (
            self.state.connection.plex_connected
            and self.state.connection.tmdb_connected
            and self.state.connection.tvdb_connected
        )
        snack = ft.SnackBar(
            content=ft.Text(
                "All connections successful!"
                if all_connected
                else f"Connection issues: {self.state.connection.error_message}"
            ),
            bgcolor=ft.Colors.GREEN if all_connected else ft.Colors.ORANGE,
        )
        self.page.overlay.append(snack)
        snack.open = True
        self.page.update()

    def _update_status_icons(self) -> None:
        """Update connection status icons based on current state."""
        # Update Plex icon
        if self.plex_status_icon:
            self.plex_status_icon.name = (
                ft.Icons.CHECK_CIRCLE if self.state.connection.plex_connected else ft.Icons.ERROR
            )
            self.plex_status_icon.color = (
                ft.Colors.GREEN if self.state.connection.plex_connected else ft.Colors.RED
            )

        # Update Plex subtitle
        if self.plex_subtitle:
            self.plex_subtitle.value = self.state.connection.plex_server_name or "Not configured"

        # Update TMDB icon
        if self.tmdb_status_icon:
            self.tmdb_status_icon.name = (
                ft.Icons.CHECK_CIRCLE if self.state.connection.tmdb_connected else ft.Icons.ERROR
            )
            self.tmdb_status_icon.color = (
                ft.Colors.GREEN if self.state.connection.tmdb_connected else ft.Colors.RED
            )

        # Update TVDB icon
        if self.tvdb_status_icon:
            self.tvdb_status_icon.name = (
                ft.Icons.CHECK_CIRCLE if self.state.connection.tvdb_connected else ft.Icons.ERROR
            )
            self.tvdb_status_icon.color = (
                ft.Colors.GREEN if self.state.connection.tvdb_connected else ft.Colors.RED
            )

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

    def _create_ignored_items_section(self) -> ft.Card:
        """Create the ignored items management section."""
        config = get_config()
        ignored_collections = config.tmdb.ignored_collections
        ignored_shows = config.tvdb.ignored_shows

        controls: list[ft.Control] = []

        # Ignored collections
        controls.append(
            ft.Text("Ignored Collections (Movies)", size=14, weight=ft.FontWeight.W_500)
        )
        if ignored_collections:
            # Build list with names, sort by name (title first)
            collection_items: list[tuple[str, int]] = []
            for coll_id in ignored_collections:
                name = self.state.ignored_collection_names.get(coll_id, "")
                collection_items.append((name, coll_id))

            # Sort by name (unknown names at end)
            collection_items.sort(key=lambda x: (x[0] == "", x[0].lower()))

            for name, coll_id in collection_items:
                # Create handler with closure
                def make_remove_handler(collection_id: int) -> Callable[[ft.ControlEvent], None]:
                    def handler(e: ft.ControlEvent) -> None:
                        self._remove_ignored_collection(collection_id)

                    return handler

                # Format: "Title | ID: xxxxx" or just "ID: xxxxx" if no name
                if name:
                    display_text = f"{name}  |  ID: {coll_id}"
                else:
                    display_text = f"ID: {coll_id}"

                controls.append(
                    ft.Row(
                        [
                            ft.Icon(ft.Icons.MOVIE, size=16, color=ft.Colors.GREY_500),
                            ft.Text(
                                display_text,
                                size=13,
                                color=ft.Colors.GREY_400,
                                expand=True,
                            ),
                            ft.IconButton(
                                icon=ft.Icons.DELETE_OUTLINE,
                                icon_size=18,
                                tooltip="Remove from ignore list",
                                on_click=make_remove_handler(coll_id),
                            ),
                        ],
                        spacing=8,
                    )
                )
        else:
            controls.append(
                ft.Text(
                    "No ignored collections",
                    size=12,
                    color=ft.Colors.GREY_500,
                    italic=True,
                )
            )

        controls.append(ft.Container(height=16))

        # Ignored shows
        controls.append(ft.Text("Ignored Shows (TV)", size=14, weight=ft.FontWeight.W_500))
        if ignored_shows:
            # Build list with names, sort by name (title first)
            show_items: list[tuple[str, int]] = []
            for show_id in ignored_shows:
                name = self.state.ignored_show_names.get(show_id, "")
                show_items.append((name, show_id))

            # Sort by name (unknown names at end)
            show_items.sort(key=lambda x: (x[0] == "", x[0].lower()))

            for name, show_id in show_items:
                # Create handler with closure
                def make_remove_handler(tvdb_id: int) -> Callable[[ft.ControlEvent], None]:
                    def handler(e: ft.ControlEvent) -> None:
                        self._remove_ignored_show(tvdb_id)

                    return handler

                # Format: "Title | ID: xxxxx" or just "ID: xxxxx" if no name
                if name:
                    display_text = f"{name}  |  ID: {show_id}"
                else:
                    display_text = f"ID: {show_id}"

                controls.append(
                    ft.Row(
                        [
                            ft.Icon(ft.Icons.TV, size=16, color=ft.Colors.GREY_500),
                            ft.Text(
                                display_text,
                                size=13,
                                color=ft.Colors.GREY_400,
                                expand=True,
                            ),
                            ft.IconButton(
                                icon=ft.Icons.DELETE_OUTLINE,
                                icon_size=18,
                                tooltip="Remove from ignore list",
                                on_click=make_remove_handler(show_id),
                            ),
                        ],
                        spacing=8,
                    )
                )
        else:
            controls.append(
                ft.Text(
                    "No ignored shows",
                    size=12,
                    color=ft.Colors.GREY_500,
                    italic=True,
                )
            )

        return self._create_section("Ignored Items", controls)

    def _remove_ignored_collection(self, collection_id: int) -> None:
        """Remove a collection from the ignore list."""
        remove_ignored_collection(collection_id)

        snack = ft.SnackBar(
            content=ft.Text(f"Collection {collection_id} removed from ignore list"),
            bgcolor=ft.Colors.GREEN,
        )
        self.page.overlay.append(snack)
        snack.open = True
        self.page.update()

    def _remove_ignored_show(self, show_id: int) -> None:
        """Remove a show from the ignore list."""
        remove_ignored_show(show_id)

        snack = ft.SnackBar(
            content=ft.Text(f"Show {show_id} removed from ignore list"),
            bgcolor=ft.Colors.GREEN,
        )
        self.page.overlay.append(snack)
        snack.open = True
        self.page.update()

    def _create_path_mapping_section(self) -> ft.Card:
        """Create the path mapping configuration section."""
        config = get_config()

        # Create text fields for path prefixes
        self.plex_prefix_field = ft.TextField(
            label="Plex Server Path Prefix",
            value=config.paths.plex_prefix or "",
            hint_text="e.g., \\\\volume1\\video",
            expand=True,
        )
        self.local_prefix_field = ft.TextField(
            label="Local Network Path Prefix",
            value=config.paths.local_prefix or "",
            hint_text="e.g., \\\\Storage4\\video",
            expand=True,
        )

        def save_paths(e: ft.ControlEvent) -> None:
            """Save the path mapping to config file."""
            import configparser

            path = get_config_path()
            if not path or not path.exists():
                snack = ft.SnackBar(
                    content=ft.Text("No config file found"),
                    bgcolor=ft.Colors.RED,
                )
                self.page.overlay.append(snack)
                snack.open = True
                self.page.update()
                return

            # Read current config
            parser = configparser.ConfigParser()
            parser.read(path, encoding="utf-8")

            # Update paths section
            if not parser.has_section("paths"):
                parser.add_section("paths")

            plex_prefix = self.plex_prefix_field.value or ""
            local_prefix = self.local_prefix_field.value or ""

            parser.set("paths", "plex_prefix", plex_prefix)
            parser.set("paths", "local_prefix", local_prefix)

            # Write back
            with open(path, "w", encoding="utf-8") as f:
                parser.write(f)

            # Reset config cache so new values are loaded
            reset_config()

            snack = ft.SnackBar(
                content=ft.Text("Path mapping saved"),
                bgcolor=ft.Colors.GREEN,
            )
            self.page.overlay.append(snack)
            snack.open = True
            self.page.update()

        return self._create_section(
            "Path Mapping",
            [
                ft.Text(
                    "Map Plex server paths to local network paths for the Folder button",
                    size=12,
                    color=ft.Colors.GREY_400,
                ),
                ft.Container(height=8),
                self.plex_prefix_field,
                self.local_prefix_field,
                ft.Row(
                    [
                        ft.ElevatedButton(
                            "Save Path Mapping",
                            icon=ft.Icons.SAVE,
                            on_click=save_paths,
                        ),
                    ],
                ),
            ],
        )

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

        # Create status icons with stored references for dynamic updates
        self.plex_status_icon = ft.Icon(
            ft.Icons.CHECK_CIRCLE if self.state.connection.plex_connected else ft.Icons.ERROR,
            color=ft.Colors.GREEN if self.state.connection.plex_connected else ft.Colors.RED,
        )
        self.plex_subtitle = ft.Text(
            self.state.connection.plex_server_name or "Not configured",
            color=ft.Colors.GREY_400,
        )
        self.tmdb_status_icon = ft.Icon(
            ft.Icons.CHECK_CIRCLE if self.state.connection.tmdb_connected else ft.Icons.ERROR,
            color=ft.Colors.GREEN if self.state.connection.tmdb_connected else ft.Colors.RED,
        )
        self.tvdb_status_icon = ft.Icon(
            ft.Icons.CHECK_CIRCLE if self.state.connection.tvdb_connected else ft.Icons.ERROR,
            color=ft.Colors.GREEN if self.state.connection.tvdb_connected else ft.Colors.RED,
        )

        # Connection section
        connection = self._create_section(
            "Connections",
            [
                ft.ListTile(
                    leading=ft.Icon(ft.Icons.DNS),
                    title=ft.Text("Plex Server"),
                    subtitle=self.plex_subtitle,
                    trailing=self.plex_status_icon,
                ),
                ft.ListTile(
                    leading=ft.Icon(ft.Icons.MOVIE),
                    title=ft.Text("TMDB"),
                    subtitle=ft.Text("Movie collection data", color=ft.Colors.GREY_400),
                    trailing=self.tmdb_status_icon,
                ),
                ft.ListTile(
                    leading=ft.Icon(ft.Icons.TV),
                    title=ft.Text("TVDB"),
                    subtitle=ft.Text("TV episode data", color=ft.Colors.GREY_400),
                    trailing=self.tvdb_status_icon,
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
                                    f"Location: {get_cache_file_path()}",
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

        # Ignored items section
        ignored_section = self._create_ignored_items_section()

        # Path mapping section
        path_mapping_section = self._create_path_mapping_section()

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
                            path_mapping_section,
                            ignored_section,
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
