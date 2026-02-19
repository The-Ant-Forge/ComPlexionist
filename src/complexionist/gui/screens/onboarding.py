"""Onboarding wizard screen for ComPlexionist GUI."""

from __future__ import annotations

import threading
from collections.abc import Callable
from typing import TYPE_CHECKING

import flet as ft

from complexionist.gui.screens.base import BaseScreen
from complexionist.gui.theme import PLEX_GOLD

if TYPE_CHECKING:
    from complexionist.gui.state import AppState


def _test_plex_connection(url: str, token: str) -> tuple[bool, str, str]:
    """Test Plex server connection.

    Returns:
        Tuple of (success, message, friendly_name).
    """
    import requests

    try:
        response = requests.get(
            f"{url.rstrip('/')}/identity",
            headers={"X-Plex-Token": token, "Accept": "application/json"},
            timeout=10,
        )
        if response.status_code == 200:
            # Try to extract friendlyName from response
            friendly_name = ""
            try:
                data = response.json()
                media_container = data.get("MediaContainer", {})
                friendly_name = media_container.get("friendlyName", "")
            except Exception:
                pass
            return True, "Connected to Plex server", friendly_name
        elif response.status_code == 401:
            return False, "Invalid Plex token", ""
        else:
            return False, f"Plex returned status {response.status_code}", ""
    except requests.exceptions.ConnectionError:
        return False, "Cannot connect to Plex server (check URL)", ""
    except requests.exceptions.Timeout:
        return False, "Connection timed out", ""
    except Exception as e:
        return False, f"Error: {e}", ""


def _test_tmdb_connection(api_key: str) -> tuple[bool, str]:
    """Test TMDB API connection.

    Returns:
        Tuple of (success, message).
    """
    import requests

    try:
        response = requests.get(
            "https://api.themoviedb.org/3/configuration",
            params={"api_key": api_key},
            timeout=10,
        )
        if response.status_code == 200:
            return True, "TMDB API key valid"
        elif response.status_code == 401:
            return False, "Invalid TMDB API key"
        else:
            return False, f"TMDB returned status {response.status_code}"
    except requests.exceptions.Timeout:
        return False, "Connection timed out"
    except Exception as e:
        return False, f"Error: {e}"


def _test_tvdb_connection(api_key: str) -> tuple[bool, str]:
    """Test TVDB API connection.

    Returns:
        Tuple of (success, message).
    """
    import requests

    try:
        response = requests.post(
            "https://api4.thetvdb.com/v4/login",
            json={"apikey": api_key},
            timeout=10,
        )
        if response.status_code == 200:
            return True, "TVDB API key valid"
        elif response.status_code == 401:
            return False, "Invalid TVDB API key"
        else:
            return False, f"TVDB returned status {response.status_code}"
    except requests.exceptions.Timeout:
        return False, "Connection timed out"
    except Exception as e:
        return False, f"Error: {e}"


class OnboardingScreen(BaseScreen):
    """First-run setup wizard screen."""

    def __init__(
        self,
        page: ft.Page,
        state: AppState,
        on_complete: Callable[[], None],
        on_back: Callable[[], None] | None = None,
    ) -> None:
        """Initialize onboarding screen.

        Args:
            page: Flet page instance.
            state: Application state.
            on_complete: Callback when setup is complete.
            on_back: Optional callback to go back (shown when accessed from settings).
        """
        super().__init__(page, state)
        self.on_complete = on_complete
        self.on_back = on_back
        self.current_step = 0
        self.steps = ["Welcome", "Plex", "TMDB", "TVDB", "Done"]

        # Load existing config to prepopulate fields
        existing_plex_url = ""
        existing_plex_token = ""
        existing_tmdb_key = ""
        existing_tvdb_key = ""

        try:
            from complexionist.config import find_config_file, get_config

            if find_config_file():
                cfg = get_config()
                existing_plex_url = cfg.plex.url or ""
                existing_plex_token = cfg.plex.token or ""
                existing_tmdb_key = cfg.tmdb.api_key or ""
                existing_tvdb_key = cfg.tvdb.api_key or ""
        except Exception:
            pass  # Ignore config loading errors

        # Form fields (prepopulated if config exists)
        self.plex_url = ft.TextField(
            label="Plex Server URL",
            hint_text="http://localhost:32400",
            prefix_icon=ft.Icons.LINK,
            value=existing_plex_url,
        )
        self.plex_token = ft.TextField(
            label="Plex Token",
            hint_text="Your X-Plex-Token",
            prefix_icon=ft.Icons.KEY,
            password=True,
            can_reveal_password=True,
            value=existing_plex_token,
        )
        self.tmdb_key = ft.TextField(
            label="TMDB API Key",
            hint_text="Your TMDB API key",
            prefix_icon=ft.Icons.KEY,
            password=True,
            can_reveal_password=True,
            value=existing_tmdb_key,
        )
        self.tvdb_key = ft.TextField(
            label="TVDB API Key",
            hint_text="Your TVDB API key",
            prefix_icon=ft.Icons.KEY,
            password=True,
            can_reveal_password=True,
            value=existing_tvdb_key,
        )

        self.status_text = ft.Text("", color=ft.Colors.GREY_400)
        self.error_text = ft.Text("", color=ft.Colors.RED)
        self.is_testing = False  # Flag to prevent double-clicks during validation
        self._plex_friendly_name = ""  # Auto-detected from Plex server

        # UI element references for dynamic updates
        self.step_indicator_row: ft.Row | None = None
        self.content_container: ft.Container | None = None
        self.back_btn: ft.TextButton | None = None
        self.next_btn: ft.ElevatedButton | None = None
        self.nav_row: ft.Row | None = None

    def _create_step_indicator(self) -> ft.Row:
        """Create the step progress indicator."""
        indicators = []
        for i, step in enumerate(self.steps):
            is_current = i == self.current_step
            is_done = i < self.current_step

            if is_done:
                icon = ft.Icon(ft.Icons.CHECK_CIRCLE, color=PLEX_GOLD, size=24)
            elif is_current:
                icon = ft.Icon(ft.Icons.RADIO_BUTTON_CHECKED, color=PLEX_GOLD, size=24)
            else:
                icon = ft.Icon(ft.Icons.RADIO_BUTTON_UNCHECKED, color=ft.Colors.GREY_600, size=24)

            indicators.append(
                ft.Column(
                    [
                        icon,
                        ft.Text(
                            step,
                            size=10,
                            color=PLEX_GOLD if (is_current or is_done) else ft.Colors.GREY_600,
                        ),
                    ],
                    horizontal_alignment=ft.CrossAxisAlignment.CENTER,
                    spacing=4,
                )
            )

            if i < len(self.steps) - 1:
                indicators.append(
                    ft.Container(
                        width=40,
                        height=2,
                        bgcolor=PLEX_GOLD if is_done else ft.Colors.GREY_700,
                    )
                )

        return ft.Row(indicators, alignment=ft.MainAxisAlignment.CENTER)

    def _get_step_content(self) -> ft.Control:
        """Get content for current step."""
        if self.current_step == 0:
            # Welcome
            return ft.Column(
                [
                    ft.Icon(ft.Icons.WAVING_HAND, size=64, color=PLEX_GOLD),
                    ft.Text("Welcome to ComPlexionist!", size=24, weight=ft.FontWeight.BOLD),
                    ft.Container(height=16),
                    ft.Text(
                        "Let's get you set up. You'll need:",
                        size=16,
                        color=ft.Colors.GREY_400,
                    ),
                    ft.Container(height=8),
                    ft.Text("• Your Plex server URL and token"),
                    ft.Text("• A TMDB API key (free)"),
                    ft.Text("• A TVDB API key"),
                    ft.Container(height=16),
                    ft.Text(
                        "This will only take a minute.",
                        size=14,
                        color=ft.Colors.GREY_500,
                    ),
                ],
                horizontal_alignment=ft.CrossAxisAlignment.CENTER,
                spacing=4,
            )
        elif self.current_step == 1:
            # Plex
            return ft.Column(
                [
                    ft.Icon(ft.Icons.DNS, size=48, color=PLEX_GOLD),
                    ft.Text("Plex Server", size=20, weight=ft.FontWeight.BOLD),
                    ft.Container(height=8),
                    ft.Text(
                        "Enter your Plex server connection details.",
                        color=ft.Colors.GREY_400,
                    ),
                    ft.Container(height=16),
                    self.plex_url,
                    self.plex_token,
                    ft.Container(height=8),
                    ft.TextButton(
                        "How to find your token",
                        icon=ft.Icons.HELP_OUTLINE,
                        url="https://support.plex.tv/articles/204059436-finding-an-authentication-token-x-plex-token/",
                    ),
                    self.status_text,
                    self.error_text,
                ],
                horizontal_alignment=ft.CrossAxisAlignment.CENTER,
                spacing=8,
                width=400,
            )
        elif self.current_step == 2:
            # TMDB
            return ft.Column(
                [
                    ft.Icon(ft.Icons.MOVIE, size=48, color=PLEX_GOLD),
                    ft.Text("TMDB API Key", size=20, weight=ft.FontWeight.BOLD),
                    ft.Container(height=8),
                    ft.Text(
                        "TMDB provides movie collection data.",
                        color=ft.Colors.GREY_400,
                    ),
                    ft.Container(height=16),
                    self.tmdb_key,
                    ft.Container(height=8),
                    ft.TextButton(
                        "Get a free API key",
                        icon=ft.Icons.OPEN_IN_NEW,
                        url="https://www.themoviedb.org/settings/api",
                    ),
                    self.status_text,
                    self.error_text,
                ],
                horizontal_alignment=ft.CrossAxisAlignment.CENTER,
                spacing=8,
                width=400,
            )
        elif self.current_step == 3:
            # TVDB
            return ft.Column(
                [
                    ft.Icon(ft.Icons.TV, size=48, color=PLEX_GOLD),
                    ft.Text("TVDB API Key", size=20, weight=ft.FontWeight.BOLD),
                    ft.Container(height=8),
                    ft.Text(
                        "TVDB provides TV episode data.",
                        color=ft.Colors.GREY_400,
                    ),
                    ft.Container(height=16),
                    self.tvdb_key,
                    ft.Container(height=8),
                    ft.TextButton(
                        "Get an API key",
                        icon=ft.Icons.OPEN_IN_NEW,
                        url="https://thetvdb.com/api-information",
                    ),
                    self.status_text,
                    self.error_text,
                ],
                horizontal_alignment=ft.CrossAxisAlignment.CENTER,
                spacing=8,
                width=400,
            )
        else:
            # Done
            return ft.Column(
                [
                    ft.Icon(ft.Icons.CHECK_CIRCLE, size=64, color=PLEX_GOLD),
                    ft.Text("You're all set!", size=24, weight=ft.FontWeight.BOLD),
                    ft.Container(height=16),
                    ft.Text(
                        "Your configuration has been saved.",
                        size=16,
                        color=ft.Colors.GREY_400,
                    ),
                    ft.Container(height=8),
                    ft.Text(
                        "Click 'Finish' to start finding gaps in your library.",
                        size=14,
                        color=ft.Colors.GREY_500,
                    ),
                ],
                horizontal_alignment=ft.CrossAxisAlignment.CENTER,
                spacing=4,
            )

    def _save_config(self) -> None:
        """Save the configuration to disk."""
        from complexionist.config import get_exe_directory, save_default_config

        # Save to the exe directory (or CWD in dev mode)
        config_path = get_exe_directory() / "complexionist.ini"

        save_default_config(
            path=config_path,
            plex_url=self.plex_url.value or "",
            plex_token=self.plex_token.value or "",
            plex_name=self._plex_friendly_name or "Plex Server",
            tmdb_api_key=self.tmdb_key.value or "",
            tvdb_api_key=self.tvdb_key.value or "",
        )

        # Update state
        self.state.config_path = str(config_path)
        self.state.has_valid_config = True

    def _next_step(self, e: ft.ControlEvent) -> None:
        """Go to next step."""
        # Prevent double-clicks during validation
        if self.is_testing:
            return

        self.error_text.value = ""

        # Validate current step before proceeding
        if self.current_step == 1:
            # Plex validation
            if not self.plex_url.value or not self.plex_token.value:
                self.error_text.value = "Please fill in all fields"
                self.page.update()
                return

            # Test Plex connection in background
            self._test_plex_and_proceed()
            return

        elif self.current_step == 2:
            # TMDB validation
            if not self.tmdb_key.value:
                self.error_text.value = "Please enter your TMDB API key"
                self.page.update()
                return

            # Test TMDB connection in background
            self._test_tmdb_and_proceed()
            return

        elif self.current_step == 3:
            # TVDB validation
            if not self.tvdb_key.value:
                self.error_text.value = "Please enter your TVDB API key"
                self.page.update()
                return

            # Test TVDB connection in background
            self._test_tvdb_and_proceed()
            return

        # For other steps (Welcome), just proceed
        if self.current_step < len(self.steps) - 1:
            self.current_step += 1
            self._rebuild()

    def _set_testing_state(self, testing: bool, message: str = "") -> None:
        """Update UI to show testing state."""
        self.is_testing = testing
        if testing:
            self.status_text.value = message
            self.status_text.color = ft.Colors.GREY_400
            self.error_text.value = ""
            # Disable the next button while testing
            if self.nav_row and len(self.nav_row.controls) >= 3:
                btn = self.nav_row.controls[2]
                if hasattr(btn, "disabled"):
                    btn.disabled = True
        else:
            self.status_text.value = ""
            # Re-enable the next button
            if self.nav_row and len(self.nav_row.controls) >= 3:
                btn = self.nav_row.controls[2]
                if hasattr(btn, "disabled"):
                    btn.disabled = False
        self.page.update()

    def _test_plex_and_proceed(self) -> None:
        """Test Plex connection and proceed if successful."""
        self._set_testing_state(True, "Testing Plex connection...")

        def do_test() -> None:
            url = self.plex_url.value or ""
            token = self.plex_token.value or ""
            success, message, friendly_name = _test_plex_connection(url, token)

            # Update UI on main thread
            async def update_ui() -> None:
                self._set_testing_state(False)
                if success:
                    self._plex_friendly_name = friendly_name
                    self.current_step += 1
                    self._rebuild()
                else:
                    self.error_text.value = message
                    self.page.update()

            self.page.run_task(update_ui)

        threading.Thread(target=do_test, daemon=True).start()

    def _test_tmdb_and_proceed(self) -> None:
        """Test TMDB connection and proceed if successful."""
        self._set_testing_state(True, "Testing TMDB API key...")

        def do_test() -> None:
            api_key = self.tmdb_key.value or ""
            success, message = _test_tmdb_connection(api_key)

            # Update UI on main thread
            async def update_ui() -> None:
                self._set_testing_state(False)
                if success:
                    self.current_step += 1
                    self._rebuild()
                else:
                    self.error_text.value = message
                    self.page.update()

            self.page.run_task(update_ui)

        threading.Thread(target=do_test, daemon=True).start()

    def _test_tvdb_and_proceed(self) -> None:
        """Test TVDB connection and proceed if successful."""
        self._set_testing_state(True, "Testing TVDB API key...")

        def do_test() -> None:
            api_key = self.tvdb_key.value or ""
            success, message = _test_tvdb_connection(api_key)

            # Update UI on main thread
            async def update_ui() -> None:
                self._set_testing_state(False)
                if success:
                    # Save config and proceed
                    self._save_config()
                    self.current_step += 1
                    self._rebuild()
                else:
                    self.error_text.value = message
                    self.page.update()

            self.page.run_task(update_ui)

        threading.Thread(target=do_test, daemon=True).start()

    def _prev_step(self, e: ft.ControlEvent) -> None:
        """Go to previous step."""
        if self.current_step > 0:
            self.current_step -= 1
            self.error_text.value = ""
            self._rebuild()

    def _finish(self, e: ft.ControlEvent) -> None:
        """Complete the wizard."""
        from complexionist.config import load_config, reset_config

        # Reload config and test connections
        reset_config()
        load_config()

        # Refresh connection state so dashboard shows correct status
        self._refresh_connection_state()

        self.on_complete()

    def _refresh_connection_state(self) -> None:
        """Test all connections and update state."""
        # Test Plex connection
        try:
            from complexionist.plex import PlexClient

            plex = PlexClient()
            plex.connect()
            self.state.connection.plex_connected = True
            self.state.connection.plex_server_name = plex.server_name or "Plex Server"

            # Get available libraries
            self.state.movie_libraries = [lib.title for lib in plex.get_movie_libraries()]
            self.state.tv_libraries = [lib.title for lib in plex.get_tv_libraries()]

            if self.state.movie_libraries:
                self.state.selected_movie_library = self.state.movie_libraries[0]
            if self.state.tv_libraries:
                self.state.selected_tv_library = self.state.tv_libraries[0]

        except Exception:
            self.state.connection.plex_connected = False

        # Test TMDB connection
        try:
            from complexionist.tmdb import TMDBClient

            tmdb = TMDBClient()
            tmdb.test_connection()
            self.state.connection.tmdb_connected = True
        except Exception:
            self.state.connection.tmdb_connected = False

        # Test TVDB connection
        try:
            from complexionist.tvdb import TVDBClient

            tvdb = TVDBClient()
            tvdb.test_connection()
            self.state.connection.tvdb_connected = True
        except Exception:
            self.state.connection.tvdb_connected = False

        # Mark config as valid if all connections succeed
        self.state.has_valid_config = (
            self.state.connection.plex_connected
            and self.state.connection.tmdb_connected
            and self.state.connection.tvdb_connected
        )

    def _rebuild(self) -> None:
        """Rebuild the UI with current state."""
        # Update the step indicator
        if self.step_indicator_row:
            new_indicator = self._create_step_indicator()
            self.step_indicator_row.controls = new_indicator.controls

        # Update the content
        if self.content_container:
            self.content_container.content = self._get_step_content()

        # Update navigation buttons
        if self.back_btn:
            self.back_btn.disabled = self.current_step == 0

        # Replace next/finish button based on step
        if self.nav_row and len(self.nav_row.controls) >= 3:
            if self.current_step == len(self.steps) - 1:
                self.nav_row.controls[2] = ft.ElevatedButton(
                    "Finish",
                    icon=ft.Icons.CHECK,
                    on_click=self._finish,
                    bgcolor=PLEX_GOLD,
                    color=ft.Colors.BLACK,
                )
            else:
                self.nav_row.controls[2] = ft.ElevatedButton(
                    "Next",
                    icon=ft.Icons.ARROW_FORWARD,
                    on_click=self._next_step,
                    bgcolor=PLEX_GOLD,
                    color=ft.Colors.BLACK,
                )

        self.page.update()

    def build(self) -> ft.Control:
        """Build the onboarding UI."""
        # Navigation buttons - store references for dynamic updates
        self.back_btn = ft.TextButton(
            "Back",
            icon=ft.Icons.ARROW_BACK,
            on_click=self._prev_step,
            disabled=self.current_step == 0,
        )

        if self.current_step == len(self.steps) - 1:
            self.next_btn = ft.ElevatedButton(
                "Finish",
                icon=ft.Icons.CHECK,
                on_click=self._finish,
                bgcolor=PLEX_GOLD,
                color=ft.Colors.BLACK,
            )
        else:
            self.next_btn = ft.ElevatedButton(
                "Next",
                icon=ft.Icons.ARROW_FORWARD,
                on_click=self._next_step,
                bgcolor=PLEX_GOLD,
                color=ft.Colors.BLACK,
            )

        # Store reference to step indicator
        self.step_indicator_row = self._create_step_indicator()

        # Store reference to content container
        self.content_container = ft.Container(
            content=self._get_step_content(),
            alignment=ft.Alignment(0, 0),
            expand=True,
        )

        # Store reference to nav row
        self.nav_row = ft.Row(
            [self.back_btn, ft.Container(expand=True), self.next_btn],
            alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
        )

        # Build content list
        content_controls: list[ft.Control] = []

        # Add header with close button if we came from settings
        if self.on_back:
            content_controls.append(
                ft.Row(
                    [
                        ft.IconButton(
                            icon=ft.Icons.CLOSE,
                            tooltip="Cancel setup",
                            on_click=lambda e: self.on_back() if self.on_back else None,
                        ),
                        ft.Text("Setup", size=20, weight=ft.FontWeight.BOLD),
                    ],
                )
            )
            content_controls.append(ft.Container(height=16))
        else:
            content_controls.append(ft.Container(height=32))

        content_controls.extend(
            [
                self.step_indicator_row,
                ft.Container(height=48),
                self.content_container,
                ft.Container(height=32),
                self.nav_row,
            ]
        )

        return ft.Container(
            content=ft.Column(
                content_controls,
                expand=True,
            ),
            padding=32,
            expand=True,
        )
