"""Dashboard screen for ComPlexionist GUI."""

from __future__ import annotations

from collections.abc import Callable
from typing import TYPE_CHECKING

import flet as ft

from complexionist.gui.screens.base import BaseScreen
from complexionist.gui.state import ScanType
from complexionist.gui.theme import PLEX_GOLD

if TYPE_CHECKING:
    from complexionist.gui.state import AppState


class DashboardScreen(BaseScreen):
    """Main dashboard/home screen."""

    def __init__(
        self,
        page: ft.Page,
        state: AppState,
        on_scan: Callable[[ScanType], None],
        on_settings: Callable[[], None],
    ) -> None:
        """Initialize dashboard screen.

        Args:
            page: Flet page instance.
            state: Application state.
            on_scan: Callback when scan is requested.
            on_settings: Callback when settings is requested.
        """
        super().__init__(page, state)
        self.on_scan = on_scan
        self.on_settings = on_settings

    def _create_status_badges(self) -> ft.Row:
        """Create connection status badges."""
        conn = self.state.connection

        def badge(label: str, connected: bool) -> ft.Container:
            color = ft.Colors.GREEN if connected else ft.Colors.RED
            icon = ft.Icons.CHECK_CIRCLE if connected else ft.Icons.ERROR
            return ft.Container(
                content=ft.Row(
                    [
                        ft.Icon(icon, color=color, size=16),
                        ft.Text(label, size=12),
                    ],
                    spacing=4,
                ),
                padding=ft.padding.symmetric(horizontal=8, vertical=4),
                border_radius=12,
                bgcolor=ft.Colors.with_opacity(0.1, color),
            )

        return ft.Row(
            [
                badge("Plex", conn.plex_connected),
                badge("TMDB", conn.tmdb_connected),
                badge("TVDB", conn.tvdb_connected),
            ],
            spacing=8,
        )

    def _create_scan_card(
        self,
        title: str,
        subtitle: str,
        icon: str,
        scan_type: ScanType,
        library_count: int,
    ) -> ft.Card:
        """Create a scan option card."""

        def on_click(e: ft.ControlEvent) -> None:
            self.on_scan(scan_type)

        return ft.Card(
            content=ft.Container(
                content=ft.Column(
                    [
                        ft.Icon(icon, size=48, color=PLEX_GOLD),
                        ft.Text(title, size=20, weight=ft.FontWeight.BOLD),
                        ft.Text(subtitle, size=14, color=ft.Colors.GREY_400),
                        ft.Text(
                            f"{library_count} {'library' if library_count == 1 else 'libraries'}",
                            size=12,
                            color=ft.Colors.GREY_500,
                        ),
                    ],
                    horizontal_alignment=ft.CrossAxisAlignment.CENTER,
                    spacing=8,
                ),
                padding=24,
                alignment=ft.Alignment(0, 0),
                on_click=on_click,
            ),
            width=200,
            height=200,
        )

    def build(self) -> ft.Control:
        """Build the dashboard UI."""
        # Header with status
        header = ft.Container(
            content=ft.Column(
                [
                    ft.Row(
                        [
                            ft.Text(
                                "ComPlexionist",
                                size=32,
                                weight=ft.FontWeight.BOLD,
                                color=PLEX_GOLD,
                            ),
                            ft.Container(expand=True),
                            self._create_status_badges(),
                        ],
                        alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
                    ),
                    ft.Text(
                        f"Connected to {self.state.connection.plex_server_name}"
                        if self.state.connection.plex_connected
                        else "Not connected",
                        size=14,
                        color=ft.Colors.GREY_400,
                    ),
                ],
            ),
            padding=ft.padding.only(bottom=32),
        )

        # Scan options
        scan_cards = ft.Row(
            [
                self._create_scan_card(
                    "Movies",
                    "Find missing collection movies",
                    ft.Icons.MOVIE_OUTLINED,
                    ScanType.MOVIES,
                    len(self.state.movie_libraries),
                ),
                self._create_scan_card(
                    "TV Shows",
                    "Find missing episodes",
                    ft.Icons.TV_OUTLINED,
                    ScanType.TV,
                    len(self.state.tv_libraries),
                ),
                self._create_scan_card(
                    "Both",
                    "Scan all libraries",
                    ft.Icons.LIBRARY_BOOKS_OUTLINED,
                    ScanType.BOTH,
                    len(self.state.movie_libraries) + len(self.state.tv_libraries),
                ),
            ],
            spacing=16,
            alignment=ft.MainAxisAlignment.CENTER,
        )

        # Quick actions
        quick_actions = ft.Row(
            [
                ft.OutlinedButton(
                    "Settings",
                    icon=ft.Icons.SETTINGS,
                    on_click=lambda e: self.on_settings(),
                ),
                ft.OutlinedButton(
                    "Clear Cache",
                    icon=ft.Icons.DELETE_SWEEP,
                ),
            ],
            spacing=8,
        )

        return ft.Container(
            content=ft.Column(
                [
                    header,
                    ft.Text("What would you like to scan?", size=18),
                    ft.Container(height=16),
                    scan_cards,
                    ft.Container(height=32),
                    ft.Divider(),
                    ft.Container(height=16),
                    ft.Text("Quick Actions", size=14, color=ft.Colors.GREY_400),
                    ft.Container(height=8),
                    quick_actions,
                ],
                horizontal_alignment=ft.CrossAxisAlignment.CENTER,
            ),
            padding=32,
            expand=True,
        )
