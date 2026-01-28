"""Main Flet application for ComPlexionist GUI."""

from __future__ import annotations

import threading

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

        # Handle window close to exit cleanly
        page.window.prevent_close = True

        async def on_window_event(e: ft.WindowEvent) -> None:
            if e.type == ft.WindowEventType.CLOSE:
                page.window.prevent_close = False
                await page.window.close()

        page.window.on_event = on_window_event

        # Try to load config and check connections
        _initialize_state(state)

        # Content container that holds the current screen
        content = ft.Container(expand=True)

        # Track previous screen for back navigation
        previous_screen: Screen | None = None

        def navigate_to(screen: Screen) -> None:
            """Navigate to a screen."""
            nonlocal previous_screen
            previous_screen = state.current_screen
            state.current_screen = screen
            _update_content()

        def start_scan(scan_type: ScanType) -> None:
            """Show library selection dialog before starting scan."""
            # Build library selection options
            controls: list[ft.Control] = []

            # Movie library dropdown (for MOVIES or BOTH)
            if scan_type in (ScanType.MOVIES, ScanType.BOTH) and state.movie_libraries:
                movie_dropdown = ft.Dropdown(
                    label="Movie Library",
                    options=[ft.dropdown.Option(lib) for lib in state.movie_libraries],
                    value=state.selected_movie_library or state.movie_libraries[0],
                    width=300,
                )
                controls.append(movie_dropdown)
            else:
                movie_dropdown = None

            # TV library dropdown (for TV or BOTH)
            if scan_type in (ScanType.TV, ScanType.BOTH) and state.tv_libraries:
                tv_dropdown = ft.Dropdown(
                    label="TV Library",
                    options=[ft.dropdown.Option(lib) for lib in state.tv_libraries],
                    value=state.selected_tv_library or state.tv_libraries[0],
                    width=300,
                )
                controls.append(tv_dropdown)
            else:
                tv_dropdown = None

            # If no libraries available, show error
            if not controls:
                page.snack_bar = ft.SnackBar(
                    content=ft.Text("No libraries available. Check your Plex connection."),
                    bgcolor=ft.Colors.RED,
                )
                page.snack_bar.open = True
                page.update()
                return

            # Create dialog first so callbacks can reference it
            scan_type_name = {
                ScanType.MOVIES: "Movie",
                ScanType.TV: "TV",
                ScanType.BOTH: "Full",
            }[scan_type]

            dialog = ft.AlertDialog(
                modal=True,
                title=ft.Text(f"Start {scan_type_name} Scan"),
                content=ft.Column(controls, spacing=16, tight=True),
                actions_alignment=ft.MainAxisAlignment.END,
            )

            def on_start(e: ft.ControlEvent) -> None:
                """Start the scan with selected libraries."""
                # Save selections
                if movie_dropdown:
                    state.selected_movie_library = movie_dropdown.value or ""
                if tv_dropdown:
                    state.selected_tv_library = tv_dropdown.value or ""

                # Close dialog and ensure it's dismissed before continuing
                dialog.open = False
                page.update()

                # Start the scan
                _begin_scan(scan_type)

            def on_cancel(e: ft.ControlEvent) -> None:
                """Cancel and close dialog."""
                dialog.open = False
                page.update()

            # Add action buttons after defining callbacks
            dialog.actions = [
                ft.TextButton("Cancel", on_click=on_cancel),
                ft.ElevatedButton(
                    "Start Scan",
                    icon=ft.Icons.PLAY_ARROW,
                    on_click=on_start,
                    bgcolor=PLEX_GOLD,
                    color=ft.Colors.BLACK,
                ),
            ]

            # Show dialog using new Flet 0.80+ API
            page.show_dialog(dialog)

        # Set up pubsub channel for progress updates from background thread
        def on_progress_message(msg: dict) -> None:
            """Handle progress update from background thread on main thread."""
            if msg.get("type") == "progress":
                phase = msg.get("phase", "")
                current = msg.get("current", 0)
                total = msg.get("total", 0)
                if state.scanning_screen is not None:
                    state.scanning_screen.update_progress(phase, current, total)
            elif msg.get("type") == "complete":
                navigate_to(Screen.RESULTS)
            elif msg.get("type") == "cancelled":
                state.scan_progress.is_running = False
                navigate_to(Screen.DASHBOARD)
            elif msg.get("type") == "error":
                state.scan_progress.is_running = False
                page.snack_bar = ft.SnackBar(
                    content=ft.Text(f"Scan error: {msg.get('error', 'Unknown error')}"),
                    bgcolor=ft.Colors.RED,
                )
                page.snack_bar.open = True
                page.update()
                navigate_to(Screen.DASHBOARD)

        page.pubsub.subscribe(on_progress_message)

        def _begin_scan(scan_type: ScanType) -> None:
            """Actually start the scan after library selection."""
            state.scan_type = scan_type
            state.reset_scan()
            state.scan_progress.is_running = True
            navigate_to(Screen.SCANNING)

            def run_scan() -> None:
                """Run the scan in a background thread."""
                try:
                    _execute_scan_with_pubsub(state, page)
                    # Signal completion via pubsub
                    page.pubsub.send_all({"type": "complete"})
                except InterruptedError:
                    # Scan was cancelled
                    page.pubsub.send_all({"type": "cancelled"})
                except Exception as e:
                    page.pubsub.send_all({"type": "error", "error": str(e)})

            # Start scan in background thread
            scan_thread = threading.Thread(target=run_scan, daemon=True)
            scan_thread.start()

        def on_theme_change(dark_mode: bool) -> None:
            """Handle theme change."""
            state.dark_mode = dark_mode
            page.theme_mode = get_theme_mode(dark_mode)
            page.update()

        # File picker for export
        def on_save_file_result(e: ft.FilePickerResultEvent) -> None:
            """Handle file save dialog result."""
            if e.path:
                try:
                    # Get the pending export data stored in the picker
                    content = file_picker.data.get("content", "")
                    with open(e.path, "w", encoding="utf-8", newline="") as f:
                        f.write(content)
                    page.snack_bar = ft.SnackBar(
                        content=ft.Text(f"Exported to {e.path}"),
                        bgcolor=ft.Colors.GREEN,
                    )
                except Exception as err:
                    page.snack_bar = ft.SnackBar(
                        content=ft.Text(f"Export failed: {err}"),
                        bgcolor=ft.Colors.RED,
                    )
                page.snack_bar.open = True
                page.update()

        file_picker = ft.FilePicker()
        file_picker.on_result = on_save_file_result
        file_picker.data = {}  # Store pending export data
        page.overlay.append(file_picker)

        def on_export(format_type: str) -> None:
            """Handle export request."""
            from datetime import date

            from complexionist.output import MovieReportFormatter, TVReportFormatter

            # Build combined content from available reports
            movie_content = ""
            tv_content = ""

            if state.movie_report:
                formatter = MovieReportFormatter(state.movie_report)
                if format_type == "csv":
                    movie_content = formatter.to_csv()
                elif format_type == "json":
                    movie_content = formatter.to_json()
                elif format_type == "clipboard":
                    movie_content = formatter.to_csv()

            if state.tv_report:
                formatter = TVReportFormatter(state.tv_report)
                if format_type == "csv":
                    tv_content = formatter.to_csv()
                elif format_type == "json":
                    tv_content = formatter.to_json()
                elif format_type == "clipboard":
                    tv_content = formatter.to_csv()

            # Combine content
            if format_type == "json":
                # For JSON, wrap both in an object if both exist
                import json

                combined = {}
                if state.movie_report:
                    combined["movies"] = json.loads(movie_content)
                if state.tv_report:
                    combined["tv"] = json.loads(tv_content)
                content = json.dumps(combined, indent=2)
            else:
                # For CSV/clipboard, concatenate with a blank line
                parts = [p for p in [movie_content, tv_content] if p]
                content = "\n".join(parts)

            if not content:
                page.snack_bar = ft.SnackBar(
                    content=ft.Text("No results to export"),
                    bgcolor=ft.Colors.ORANGE,
                )
                page.snack_bar.open = True
                page.update()
                return

            if format_type == "clipboard":
                # Copy to clipboard
                page.set_clipboard(content)
                page.snack_bar = ft.SnackBar(
                    content=ft.Text("Results copied to clipboard"),
                    bgcolor=ft.Colors.GREEN,
                )
                page.snack_bar.open = True
                page.update()
            else:
                # Show file save dialog
                today = date.today().isoformat()
                ext = "csv" if format_type == "csv" else "json"
                file_picker.data["content"] = content
                file_picker.save_file(
                    dialog_title=f"Export as {ext.upper()}",
                    file_name=f"complexionist_gaps_{today}.{ext}",
                    file_type=ft.FilePickerFileType.CUSTOM,
                    allowed_extensions=[ext],
                )

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
                # Show back button if we came from settings
                on_back = (
                    (lambda: navigate_to(Screen.SETTINGS))
                    if previous_screen == Screen.SETTINGS
                    else None
                )
                screen = OnboardingScreen(
                    page,
                    state,
                    on_complete=lambda: navigate_to(Screen.DASHBOARD),
                    on_back=on_back,
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
                # Store reference so _execute_scan can update the UI
                state.scanning_screen = screen
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
                    on_setup=lambda: navigate_to(Screen.ONBOARDING),
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


def _execute_scan_with_pubsub(state: AppState, page: ft.Page) -> None:
    """Execute the scan using pubsub for thread-safe UI updates.

    Args:
        state: Application state with scan configuration.
        page: Flet page for pubsub communication.
    """
    import time

    from complexionist.cache import Cache
    from complexionist.gaps import EpisodeGapFinder, MovieGapFinder
    from complexionist.gui.state import ScanStats
    from complexionist.plex import PlexClient
    from complexionist.statistics import ScanStatistics
    from complexionist.tmdb import TMDBClient
    from complexionist.tvdb import TVDBClient

    # Start statistics tracking
    stats = ScanStatistics()
    stats.start()
    start_time = time.time()

    def update_progress(phase: str, current: int, total: int) -> None:
        """Send progress update via pubsub for main thread handling."""
        if state.scan_progress.is_cancelled:
            raise InterruptedError("Scan cancelled by user")

        state.scan_progress.phase = phase
        state.scan_progress.current = current
        state.scan_progress.total = total

        # Send progress via pubsub - handled on main thread
        page.pubsub.send_all(
            {
                "type": "progress",
                "phase": phase,
                "current": current,
                "total": total,
            }
        )

    # Show initialization steps
    update_progress("Loading cache...", 0, 0)
    cache = Cache()
    update_progress("Cache loaded", 0, 0)

    update_progress("Connecting to Plex...", 0, 0)
    plex = PlexClient()
    plex.connect()
    update_progress("Connected to Plex", 0, 0)

    try:
        # Run movie scan if requested
        if state.scan_type in (ScanType.MOVIES, ScanType.BOTH):
            update_progress("Initializing TMDB client...", 0, 0)
            tmdb = TMDBClient(cache=cache)
            update_progress("TMDB client ready", 0, 0)

            finder = MovieGapFinder(
                plex_client=plex,
                tmdb_client=tmdb,
                progress_callback=update_progress,
            )

            library = state.selected_movie_library or None
            state.movie_report = finder.find_gaps(library)

        # Run TV scan if requested
        if state.scan_type in (ScanType.TV, ScanType.BOTH):
            update_progress("Initializing TVDB client...", 0, 0)
            tvdb = TVDBClient(cache=cache)
            update_progress("TVDB client ready", 0, 0)

            finder = EpisodeGapFinder(
                plex_client=plex,
                tvdb_client=tvdb,
                progress_callback=update_progress,
            )

            library = state.selected_tv_library or None
            state.tv_report = finder.find_gaps(library)

    finally:
        # Always flush cache
        cache.flush()

    # Stop statistics tracking
    stats.stop()

    # Store statistics in state for results page
    state.scan_stats = ScanStats(
        duration_seconds=time.time() - start_time,
        api_calls=stats.total_api_calls,
        cache_hits=stats.cache_hits,
        cache_misses=stats.cache_misses,
        plex_calls=stats.plex_requests,
        tmdb_calls=stats.total_tmdb_calls,
        tvdb_calls=stats.total_tvdb_calls,
    )

    # Mark scan complete
    state.scan_progress.is_running = False
