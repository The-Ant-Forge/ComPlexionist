"""Onboarding wizard screen for ComPlexionist GUI."""

from __future__ import annotations

from collections.abc import Callable
from typing import TYPE_CHECKING

import flet as ft

from complexionist.gui.screens.base import BaseScreen
from complexionist.gui.theme import PLEX_GOLD

if TYPE_CHECKING:
    from complexionist.gui.state import AppState


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

        # Form fields
        self.plex_url = ft.TextField(
            label="Plex Server URL",
            hint_text="http://localhost:32400",
            prefix_icon=ft.Icons.LINK,
        )
        self.plex_token = ft.TextField(
            label="Plex Token",
            hint_text="Your X-Plex-Token",
            prefix_icon=ft.Icons.KEY,
            password=True,
            can_reveal_password=True,
        )
        self.tmdb_key = ft.TextField(
            label="TMDB API Key",
            hint_text="Your TMDB API key",
            prefix_icon=ft.Icons.KEY,
            password=True,
            can_reveal_password=True,
        )
        self.tvdb_key = ft.TextField(
            label="TVDB API Key",
            hint_text="Your TVDB API key",
            prefix_icon=ft.Icons.KEY,
            password=True,
            can_reveal_password=True,
        )

        self.status_text = ft.Text("", color=ft.Colors.GREY_400)
        self.error_text = ft.Text("", color=ft.Colors.RED)

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
            tmdb_api_key=self.tmdb_key.value or "",
            tvdb_api_key=self.tvdb_key.value or "",
        )

        # Update state
        self.state.config_path = str(config_path)
        self.state.has_valid_config = True

    def _next_step(self, e: ft.ControlEvent) -> None:
        """Go to next step."""
        self.error_text.value = ""

        # Validate current step before proceeding
        if self.current_step == 1:
            if not self.plex_url.value or not self.plex_token.value:
                self.error_text.value = "Please fill in all fields"
                self.update()
                return
            # TODO: Test Plex connection

        elif self.current_step == 2:
            if not self.tmdb_key.value:
                self.error_text.value = "Please enter your TMDB API key"
                self.update()
                return
            # TODO: Test TMDB connection

        elif self.current_step == 3:
            if not self.tvdb_key.value:
                self.error_text.value = "Please enter your TVDB API key"
                self.update()
                return
            # Save the config
            self._save_config()

        if self.current_step < len(self.steps) - 1:
            self.current_step += 1
            self._rebuild()

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

        self.on_complete()

    def _rebuild(self) -> None:
        """Rebuild the UI with current state."""
        # Find and update the content container
        self.page.update()

    def build(self) -> ft.Control:
        """Build the onboarding UI."""
        # Navigation buttons
        back_btn = ft.TextButton(
            "Back",
            icon=ft.Icons.ARROW_BACK,
            on_click=self._prev_step,
            disabled=self.current_step == 0,
        )

        if self.current_step == len(self.steps) - 1:
            next_btn = ft.ElevatedButton(
                "Finish",
                icon=ft.Icons.CHECK,
                on_click=self._finish,
                bgcolor=PLEX_GOLD,
                color=ft.Colors.BLACK,
            )
        else:
            next_btn = ft.ElevatedButton(
                "Next",
                icon=ft.Icons.ARROW_FORWARD,
                on_click=self._next_step,
                bgcolor=PLEX_GOLD,
                color=ft.Colors.BLACK,
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
                self._create_step_indicator(),
                ft.Container(height=48),
                ft.Container(
                    content=self._get_step_content(),
                    alignment=ft.Alignment(0, 0),
                    expand=True,
                ),
                ft.Container(height=32),
                ft.Row(
                    [back_btn, ft.Container(expand=True), next_btn],
                    alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
                ),
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
