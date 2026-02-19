"""Main Flet application for ComPlexionist GUI."""

from __future__ import annotations

import asyncio
import os
import sys
import threading
from typing import Any

import flet as ft

from complexionist.gui.state import AppState, ScanType, Screen
from complexionist.gui.theme import PLEX_GOLD, create_theme, get_theme_mode

# Track if we're shutting down to prevent multiple cleanup attempts
_shutting_down = False

# Watchdog timer reference — cancelled on clean shutdown, fires on hang
_watchdog_timer: threading.Timer | None = None


def _kill_flet_process() -> None:
    """Kill the Flet desktop client process (Windows only).

    Targets flet.exe by image name, then force-exits our Python process.
    This avoids the race condition of trying to kill our own process tree.
    """
    if sys.platform != "win32":
        return

    try:
        import subprocess

        # Kill flet.exe by image name — this is the Flutter desktop client
        subprocess.run(
            ["taskkill", "/F", "/IM", "flet.exe"],
            capture_output=True,
            timeout=5,
        )
    except Exception:
        pass


def _watchdog_exit() -> None:
    """Last-resort forced exit if Flet's normal shutdown hangs.

    Called by a non-daemon timer thread. Kills flet.exe, then our process.
    """
    _kill_flet_process()
    os._exit(1)


def _suppress_windows_close_error() -> None:
    """Suppress harmless ConnectionResetError on Windows when closing the app.

    This error occurs in asyncio's proactor event loop when the Flet window
    is closed and the underlying socket is terminated. It's cosmetic only.
    """
    if sys.platform != "win32":
        return

    def custom_exception_handler(loop: asyncio.AbstractEventLoop, context: dict[str, Any]) -> None:
        exception = context.get("exception")
        # Suppress ConnectionResetError during shutdown
        if isinstance(exception, ConnectionResetError):
            return
        # Use default handler for other exceptions
        loop.default_exception_handler(context)

    # Install the handler for any future event loops
    asyncio.set_event_loop_policy(_SuppressingEventLoopPolicy(custom_exception_handler))


class _SuppressingEventLoopPolicy(asyncio.DefaultEventLoopPolicy):
    """Event loop policy that installs a custom exception handler."""

    def __init__(
        self,
        exception_handler: Any,
    ) -> None:
        super().__init__()
        self._exception_handler = exception_handler

    def new_event_loop(self) -> asyncio.AbstractEventLoop:
        loop = super().new_event_loop()
        loop.set_exception_handler(self._exception_handler)
        return loop


def run_app(web_mode: bool = False) -> None:
    """Run the ComPlexionist GUI application.

    Args:
        web_mode: If True, opens in a web browser instead of native window.
    """
    # Suppress harmless asyncio error on Windows when closing window
    _suppress_windows_close_error()

    def main(page: ft.Page) -> None:
        """Main application entry point."""
        from complexionist.gui.window_state import (
            apply_window_state,
            capture_window_state,
            load_window_state,
            save_window_state,
            validate_window_position,
        )

        # Load and apply saved window state (window starts hidden via FLET_APP_HIDDEN)
        if not web_mode:
            window_state = load_window_state()
            window_state = validate_window_position(window_state, 3840, 2160)
            apply_window_state(page, window_state)

            # Set minimum constraints
            page.window.min_width = 800
            page.window.min_height = 600

            # Commit window settings before adding content
            page.update()

        # Initialize state
        state = AppState()

        # Configure page basics
        page.title = "ComPlexionist"
        page.theme = create_theme(dark_mode=True)
        page.theme_mode = get_theme_mode(dark_mode=True)

        # Set window icon (from assets directory)
        if not web_mode:
            page.window.icon = "icon.png"

            # Intercept window close so we receive the CLOSE event.
            # Without this, the OS closes the window directly and Python
            # never hears about it — causing orphaned processes.
            page.window.prevent_close = True

        # Handle window close: save state, show closing screen, shut down.
        # A watchdog timer ensures we exit even if Flet's cleanup hangs.
        def on_window_event(e: ft.WindowEvent) -> None:
            global _shutting_down, _watchdog_timer
            if e.type == ft.WindowEventType.CLOSE:
                if _shutting_down:
                    return
                _shutting_down = True

                # Save window state before closing
                if not web_mode:
                    current_state = capture_window_state(page)
                    save_window_state(current_state)

                # Show a "Closing" screen so the user knows we're shutting down
                page.controls.clear()
                page.add(
                    ft.Container(
                        content=ft.Column(
                            [
                                ft.ProgressRing(width=32, height=32),
                                ft.Text("Closing...", size=16),
                            ],
                            alignment=ft.MainAxisAlignment.CENTER,
                            horizontal_alignment=ft.CrossAxisAlignment.CENTER,
                            spacing=16,
                        ),
                        expand=True,
                        alignment=ft.Alignment(0, 0),
                    )
                )

                # Start a NON-daemon watchdog: if Flet hasn't shut down in
                # 2 seconds, kill flet.exe and force-exit. Non-daemon ensures
                # the timer survives Python's shutdown sequence (daemon threads
                # get killed during shutdown, which was causing the timer to
                # never fire). Cancelled on clean exit after ft.app() returns.
                _watchdog_timer = threading.Timer(2.0, _watchdog_exit)
                _watchdog_timer.daemon = False
                _watchdog_timer.start()

                # Tell Flet to destroy the window. This triggers the Flutter
                # process to exit, which unblocks Flet's internal wait loop
                # and lets Python shut down through the normal path.
                page.window.destroy()

        page.window.on_event = on_window_event

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
                snack = ft.SnackBar(
                    content=ft.Text("No libraries available. Check your Plex connection."),
                    bgcolor=ft.Colors.RED,
                )
                page.overlay.append(snack)
                snack.open = True
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
                    autofocus=True,  # Focus button immediately so first click works
                ),
            ]

            # Show dialog using new Flet 0.80+ API and ensure focus
            page.show_dialog(dialog)
            page.update()

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
                from complexionist.gui.errors import show_error

                show_error(
                    page,
                    f"Scan error: {msg.get('error', 'Unknown error')}",
                    context="Scan",
                    persistent=True,
                )
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

        def on_export(format_type: str) -> None:
            """Handle export request."""
            from datetime import date
            from pathlib import Path

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
                snack = ft.SnackBar(
                    content=ft.Text("No results to export"),
                    bgcolor=ft.Colors.ORANGE,
                )
                page.overlay.append(snack)
                snack.open = True
                page.update()
                return

            if format_type == "clipboard":
                # Copy to clipboard (Flet uses clipboard property, not set_clipboard)
                page.clipboard = content
                snack = ft.SnackBar(
                    content=ft.Text("Results copied to clipboard"),
                    bgcolor=ft.Colors.GREEN,
                )
                page.overlay.append(snack)
                snack.open = True
                page.update()
            else:
                # Build filename matching CLI pattern: {library}_{type}_gaps_{date}.{ext}
                def sanitize(name: str) -> str:
                    safe = "".join(c if c.isalnum() or c in " -_" else "_" for c in name)
                    return safe.replace(" ", "_")

                today = date.today().isoformat()
                ext = "csv" if format_type == "csv" else "json"

                # Determine filename based on what was scanned
                if state.movie_report and state.tv_report:
                    # Both - use movie library name + "full"
                    lib_name = sanitize(state.movie_report.library_name)
                    filename = f"{lib_name}_full_gaps_{today}.{ext}"
                elif state.movie_report:
                    lib_name = sanitize(state.movie_report.library_name)
                    filename = f"{lib_name}_movie_gaps_{today}.{ext}"
                elif state.tv_report:
                    lib_name = sanitize(state.tv_report.library_name)
                    filename = f"{lib_name}_tv_gaps_{today}.{ext}"
                else:
                    filename = f"complexionist_gaps_{today}.{ext}"

                filepath = Path.cwd() / filename

                try:
                    with open(filepath, "w", encoding="utf-8", newline="") as f:
                        f.write(content)

                    # Store filepath in a variable the closure can access
                    saved_path = filepath

                    def open_location(e: ft.ControlEvent) -> None:
                        """Open file explorer at the save location."""
                        import subprocess
                        import sys

                        if sys.platform == "win32":
                            # Windows: open explorer and select the file
                            subprocess.run(["explorer", "/select,", str(saved_path)])
                        elif sys.platform == "darwin":
                            # macOS: open Finder
                            subprocess.run(["open", str(saved_path.parent)])
                        else:
                            # Linux: try xdg-open
                            subprocess.run(["xdg-open", str(saved_path.parent)])

                    snack = ft.SnackBar(
                        content=ft.Row(
                            [
                                ft.Text(f"Saved: {filepath.name}"),
                                ft.TextButton(
                                    "Open folder",
                                    on_click=open_location,
                                    style=ft.ButtonStyle(color=ft.Colors.WHITE),
                                ),
                            ],
                            alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
                            expand=True,
                        ),
                        bgcolor=ft.Colors.GREEN,
                        duration=6000,  # Show for 6 seconds to give time to click
                    )
                except Exception as err:
                    snack = ft.SnackBar(
                        content=ft.Text(f"Export failed: {err}"),
                        bgcolor=ft.Colors.RED,
                    )
                page.overlay.append(snack)
                snack.open = True
                page.update()

        def _update_content() -> None:
            """Update the content based on current screen."""
            # Import screens here to avoid circular imports
            from complexionist.gui.screens import (
                DashboardScreen,
                HelpScreen,
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
            elif state.current_screen == Screen.HELP:
                screen = HelpScreen(
                    page,
                    state,
                    on_back=lambda: navigate_to(Screen.DASHBOARD),
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
            elif idx == 3:
                navigate_to(Screen.HELP)

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
                ft.NavigationRailDestination(
                    icon=ft.Icons.HELP_OUTLINE,
                    selected_icon=ft.Icons.HELP,
                    label="Help",
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

        # Show UI immediately, then initialize in background
        # This makes the app feel responsive - window appears while connections are tested
        async def async_init() -> None:
            """Initialize state in background after UI is visible."""
            import asyncio

            # Small delay to ensure UI is rendered first
            await asyncio.sleep(0.05)

            # Run initialization (this does network calls)
            _initialize_state(state)

            # Mark checking complete
            state.connection.is_checking = False

            # Refresh UI with actual connection status
            _update_content()

        # Determine initial screen (before we know connection status)
        # Check config file existence synchronously (fast, no network)
        from complexionist.config import find_config_file, has_valid_config

        config_file = find_config_file()
        if config_file:
            state.config_path = str(config_file)
        state.has_valid_config = has_valid_config()

        if not state.has_valid_config:
            # No config - go straight to onboarding (no async init needed)
            state.connection.is_checking = False
            navigate_to(Screen.ONBOARDING)
        else:
            # Show dashboard immediately with "Checking..." indicators
            navigate_to(Screen.DASHBOARD)
            # Then run connection tests in background
            page.run_task(async_init)

        # Now show the window (everything is set up)
        if not web_mode:
            page.window.visible = True
            page.update()

    # Run the app
    # Get assets directory path (relative to package or cwd for dev)
    import sys
    from pathlib import Path

    # Try to find assets directory - check multiple locations
    if getattr(sys, "frozen", False):
        # Running as PyInstaller bundle - assets are in the temp extraction dir
        assets_dir = str(Path(sys._MEIPASS) / "assets")  # noqa: SLF001  # PyInstaller attr
    else:
        # Running from source - assets are relative to project root
        assets_dir = str(Path(__file__).parent.parent.parent.parent / "assets")

    if web_mode:
        ft.app(target=main, view=ft.AppView.WEB_BROWSER, assets_dir=assets_dir)
    else:
        # Start hidden to prevent window flashing during setup
        ft.app(target=main, view=ft.AppView.FLET_APP_HIDDEN, assets_dir=assets_dir)

    # ft.app() returned — cancel the watchdog timer if it was started.
    if _watchdog_timer is not None:
        _watchdog_timer.cancel()

    # Force-exit to ensure no stray threads keep the process alive.
    # All Flet cleanup (close_flet_view, conn.close) has already run
    # inside ft.app(). Window state was saved in on_window_event.
    os._exit(0)


def _initialize_state(state: AppState) -> None:
    """Initialize application state by testing connections.

    Note: Config validation is done synchronously before this is called.
    This function focuses on network operations that can run in background.

    Args:
        state: Application state to initialize.
    """
    try:
        from complexionist.config import get_config

        # Test connections to services (this is the slow part)
        if state.has_valid_config:
            cfg = get_config()
            _test_connections(state, cfg)

    except Exception as e:
        state.connection.error_message = str(e)


def _test_connections(state: AppState, cfg: object) -> None:
    """Test connections to Plex, TMDB, and TVDB.

    Args:
        state: Application state to update.
        cfg: Configuration object (unused, kept for API compatibility).
    """
    from complexionist.validation import test_connections

    result = test_connections()

    # Update Plex state
    state.connection.plex_connected = result.plex_ok
    state.connection.plex_server_name = result.plex_server_name
    state.movie_libraries = result.movie_libraries
    state.tv_libraries = result.tv_libraries

    if state.movie_libraries:
        state.selected_movie_library = state.movie_libraries[0]
    if state.tv_libraries:
        state.selected_tv_library = state.tv_libraries[0]

    # Update TMDB/TVDB state
    state.connection.tmdb_connected = result.tmdb_ok
    state.connection.tvdb_connected = result.tvdb_ok


def _execute_scan_with_pubsub(state: AppState, page: ft.Page) -> None:
    """Execute the scan using pubsub for thread-safe UI updates.

    Args:
        state: Application state with scan configuration.
        page: Flet page for pubsub communication.
    """

    from complexionist.api.base import BaseAPIClient
    from complexionist.cache import Cache
    from complexionist.config import get_config
    from complexionist.gaps import EpisodeGapFinder, MovieGapFinder
    from complexionist.plex import PlexClient
    from complexionist.statistics import ScanStatistics
    from complexionist.tmdb import TMDBClient
    from complexionist.tvdb import TVDBClient

    # Load config for ignored lists
    config = get_config()

    # Start statistics tracking
    stats = ScanStatistics()
    stats.start()

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

    # Track API clients so we can close them after the scan.
    # Unclosed httpx connections prevent Flet from shutting down cleanly.
    api_clients: list[BaseAPIClient] = []

    try:
        # Run movie scan if requested
        if state.scan_type in (ScanType.MOVIES, ScanType.BOTH):
            update_progress("Initializing TMDB client...", 0, 0)
            tmdb = TMDBClient(cache=cache)
            api_clients.append(tmdb)
            update_progress("TMDB client ready", 0, 0)

            finder = MovieGapFinder(
                plex_client=plex,
                tmdb_client=tmdb,
                ignored_collection_ids=config.tmdb.ignored_collections,
                progress_callback=update_progress,
            )

            library = state.selected_movie_library or None
            state.movie_report = finder.find_gaps(library)

        # Run TV scan if requested
        if state.scan_type in (ScanType.TV, ScanType.BOTH):
            update_progress("Initializing TVDB client...", 0, 0)
            tvdb = TVDBClient(cache=cache)
            api_clients.append(tvdb)
            update_progress("TVDB client ready", 0, 0)

            finder = EpisodeGapFinder(
                plex_client=plex,
                tvdb_client=tvdb,
                ignored_show_ids=config.tvdb.ignored_shows,
                progress_callback=update_progress,
            )

            library = state.selected_tv_library or None
            state.tv_report = finder.find_gaps(library)

    finally:
        # Close all API clients to release httpx connections
        for client in api_clients:
            client.close()

        # Close PlexServer's requests.Session (HTTP keep-alive pool).
        # Unclosed sessions can interfere with Flet's event loop shutdown.
        if plex._server is not None and hasattr(plex._server, "_session"):
            plex._server._session.close()

        # Always flush cache, then prune expired entries during idle time
        cache.flush()
        cache.cleanup_expired()

    # Stop statistics tracking
    stats.stop()

    # Store statistics directly in state for results page
    state.scan_stats = stats

    # Mark scan complete
    state.scan_progress.is_running = False
