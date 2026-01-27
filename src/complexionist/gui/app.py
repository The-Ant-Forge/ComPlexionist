"""Main Flet application for ComPlexionist GUI."""

from __future__ import annotations

import flet as ft

from complexionist.gui.state import AppState, ScanType, Screen
from complexionist.gui.theme import PLEX_GOLD, create_theme, get_theme_mode


def run_app(web_mode: bool = False) -> None:
    """Run the ComPlexionist GUI application.

    Args:
        web_mode: If True, opens in a web browser instead of native window.
    """

    def main(page: ft.Page) -> None:
        """Main application entry point."""
        # Initialize state
        state = AppState()

        # Configure page
        page.title = "ComPlexionist"
        page.theme = create_theme(dark_mode=True)
        page.theme_mode = get_theme_mode(dark_mode=True)
        page.window.width = 1000
        page.window.height = 700
        page.window.min_width = 800
        page.window.min_height = 600

        # Try to load config and check connections
        _initialize_state(state)

        # Content container that holds the current screen
        content = ft.Container(expand=True)

        def navigate_to(screen: Screen) -> None:
            """Navigate to a screen."""
            state.current_screen = screen
            _update_content()

        def start_scan(scan_type: ScanType) -> None:
            """Start a scan of the specified type."""
            state.scan_type = scan_type
            state.reset_scan()
            navigate_to(Screen.SCANNING)
            # TODO: Start actual scan in background thread

        def on_theme_change(dark_mode: bool) -> None:
            """Handle theme change."""
            state.dark_mode = dark_mode
            page.theme_mode = get_theme_mode(dark_mode)
            page.update()

        def on_export(format_type: str) -> None:
            """Handle export request."""
            # TODO: Implement export
            page.snack_bar = ft.SnackBar(
                content=ft.Text(f"Export to {format_type} not yet implemented"),
            )
            page.snack_bar.open = True
            page.update()

        def _update_content() -> None:
            """Update the content based on current screen."""
            # Import screens here to avoid circular imports
            from complexionist.gui.screens import (
                DashboardScreen,
                OnboardingScreen,
                ResultsScreen,
                ScanningScreen,
                SettingsScreen,
            )

            if state.current_screen == Screen.ONBOARDING:
                screen = OnboardingScreen(
                    page,
                    state,
                    on_complete=lambda: navigate_to(Screen.DASHBOARD),
                )
            elif state.current_screen == Screen.DASHBOARD:
                screen = DashboardScreen(
                    page,
                    state,
                    on_scan=start_scan,
                    on_settings=lambda: navigate_to(Screen.SETTINGS),
                )
            elif state.current_screen == Screen.SCANNING:
                screen = ScanningScreen(
                    page,
                    state,
                    on_cancel=lambda: navigate_to(Screen.DASHBOARD),
                    on_complete=lambda: navigate_to(Screen.RESULTS),
                )
            elif state.current_screen == Screen.RESULTS:
                screen = ResultsScreen(
                    page,
                    state,
                    on_back=lambda: navigate_to(Screen.DASHBOARD),
                    on_export=on_export,
                )
            elif state.current_screen == Screen.SETTINGS:
                screen = SettingsScreen(
                    page,
                    state,
                    on_back=lambda: navigate_to(Screen.DASHBOARD),
                    on_theme_change=on_theme_change,
                )
            else:
                screen = DashboardScreen(
                    page,
                    state,
                    on_scan=start_scan,
                    on_settings=lambda: navigate_to(Screen.SETTINGS),
                )

            content.content = screen.build()
            page.update()

        # Build navigation rail
        def on_nav_change(e: ft.ControlEvent) -> None:
            """Handle navigation selection."""
            idx = e.control.selected_index
            if idx == 0:
                navigate_to(Screen.DASHBOARD)
            elif idx == 1:
                navigate_to(Screen.RESULTS)
            elif idx == 2:
                navigate_to(Screen.SETTINGS)

        nav_rail = ft.NavigationRail(
            selected_index=0,
            label_type=ft.NavigationRailLabelType.ALL,
            min_width=80,
            min_extended_width=200,
            destinations=[
                ft.NavigationRailDestination(
                    icon=ft.Icons.HOME_OUTLINED,
                    selected_icon=ft.Icons.HOME,
                    label="Home",
                ),
                ft.NavigationRailDestination(
                    icon=ft.Icons.LIST_OUTLINED,
                    selected_icon=ft.Icons.LIST,
                    label="Results",
                ),
                ft.NavigationRailDestination(
                    icon=ft.Icons.SETTINGS_OUTLINED,
                    selected_icon=ft.Icons.SETTINGS,
                    label="Settings",
                ),
            ],
            on_change=on_nav_change,
            bgcolor=ft.Colors.with_opacity(0.05, PLEX_GOLD),
        )

        # Main layout
        page.add(
            ft.Row(
                [
                    nav_rail,
                    ft.VerticalDivider(width=1),
                    content,
                ],
                expand=True,
            )
        )

        # Determine initial screen
        if not state.has_valid_config:
            navigate_to(Screen.ONBOARDING)
        else:
            navigate_to(Screen.DASHBOARD)

    # Run the app
    if web_mode:
        ft.app(target=main, view=ft.AppView.WEB_BROWSER)
    else:
        ft.app(target=main)


def _initialize_state(state: AppState) -> None:
    """Initialize application state by checking config and connections.

    Args:
        state: Application state to initialize.
    """
    try:
        from complexionist.config import find_config_file, get_config

        config_file = find_config_file()
        if config_file:
            state.config_path = str(config_file)
            cfg = get_config()

            # Check if we have minimum required config
            state.has_valid_config = bool(
                cfg.plex.url and cfg.plex.token and cfg.tmdb.api_key and cfg.tvdb.api_key
            )

            if state.has_valid_config:
                # Try to connect to services
                _test_connections(state, cfg)
        else:
            state.has_valid_config = False

    except Exception as e:
        state.has_valid_config = False
        state.connection.error_message = str(e)


def _test_connections(state: AppState, cfg: object) -> None:
    """Test connections to Plex, TMDB, and TVDB.

    Args:
        state: Application state to update.
        cfg: Configuration object.
    """
    # Test Plex connection
    try:
        from complexionist.plex import PlexClient

        plex = PlexClient()
        plex.connect()
        state.connection.plex_connected = True
        state.connection.plex_server_name = plex.server_name or "Plex Server"

        # Get available libraries
        state.movie_libraries = [lib.title for lib in plex.get_movie_libraries()]
        state.tv_libraries = [lib.title for lib in plex.get_tv_libraries()]

        if state.movie_libraries:
            state.selected_movie_library = state.movie_libraries[0]
        if state.tv_libraries:
            state.selected_tv_library = state.tv_libraries[0]

    except Exception:
        state.connection.plex_connected = False

    # Test TMDB connection
    try:
        from complexionist.tmdb import TMDBClient

        tmdb = TMDBClient()
        tmdb.test_connection()
        state.connection.tmdb_connected = True
    except Exception:
        state.connection.tmdb_connected = False

    # Test TVDB connection
    try:
        from complexionist.tvdb import TVDBClient

        tvdb = TVDBClient()
        tvdb.test_connection()
        state.connection.tvdb_connected = True
    except Exception:
        state.connection.tvdb_connected = False
