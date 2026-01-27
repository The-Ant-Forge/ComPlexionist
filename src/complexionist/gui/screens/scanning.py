"""Scanning progress screen for ComPlexionist GUI."""

from __future__ import annotations

from collections.abc import Callable
from typing import TYPE_CHECKING

import flet as ft

from complexionist.gui.screens.base import BaseScreen
from complexionist.gui.state import ScanType
from complexionist.gui.theme import PLEX_GOLD

if TYPE_CHECKING:
    from complexionist.gui.state import AppState


class ScanningScreen(BaseScreen):
    """Scanning progress display screen."""

    def __init__(
        self,
        page: ft.Page,
        state: AppState,
        on_cancel: Callable[[], None],
        on_complete: Callable[[], None],
    ) -> None:
        """Initialize scanning screen.

        Args:
            page: Flet page instance.
            state: Application state.
            on_cancel: Callback when scan is cancelled.
            on_complete: Callback when scan completes.
        """
        super().__init__(page, state)
        self.on_cancel = on_cancel
        self.on_complete = on_complete

        # UI elements that need updating
        self.progress_bar = ft.ProgressBar(width=400, color=PLEX_GOLD, value=0)
        self.progress_text = ft.Text("Preparing...", size=14)
        self.stats_text = ft.Text("", size=12, color=ft.Colors.GREY_400)
        self.phase_text = ft.Text("", size=16)

    def _get_scan_icon(self) -> str:
        """Get icon for current scan type."""
        if self.state.scan_type == ScanType.MOVIES:
            return ft.Icons.MOVIE_OUTLINED
        elif self.state.scan_type == ScanType.TV:
            return ft.Icons.TV_OUTLINED
        else:
            return ft.Icons.LIBRARY_BOOKS_OUTLINED

    def _get_scan_title(self) -> str:
        """Get title for current scan type."""
        if self.state.scan_type == ScanType.MOVIES:
            return "Scanning Movie Collections"
        elif self.state.scan_type == ScanType.TV:
            return "Scanning TV Shows"
        else:
            return "Scanning Libraries"

    def update_progress(self, phase: str, current: int, total: int) -> None:
        """Update the progress display.

        Args:
            phase: Current phase description.
            current: Current item number.
            total: Total items to process.
        """
        self.state.scan_progress.phase = phase
        self.state.scan_progress.current = current
        self.state.scan_progress.total = total

        # Update UI
        if total > 0:
            self.progress_bar.value = current / total
            self.progress_text.value = f"{current} / {total}"
        else:
            self.progress_bar.value = None  # Indeterminate
            self.progress_text.value = "Processing..."

        self.phase_text.value = phase
        self.update()

    def scan_complete(self) -> None:
        """Called when scan is complete."""
        self.progress_bar.value = 1.0
        self.phase_text.value = "Complete!"
        self.progress_text.value = "Scan finished"
        self.update()
        self.on_complete()

    def _cancel_scan(self, e: ft.ControlEvent) -> None:
        """Cancel the current scan."""
        self.state.scan_progress.is_cancelled = True
        self.on_cancel()

    def build(self) -> ft.Control:
        """Build the scanning UI."""
        return ft.Container(
            content=ft.Column(
                [
                    ft.Icon(self._get_scan_icon(), size=64, color=PLEX_GOLD),
                    ft.Container(height=16),
                    ft.Text(
                        self._get_scan_title(),
                        size=24,
                        weight=ft.FontWeight.BOLD,
                    ),
                    ft.Container(height=8),
                    self.phase_text,
                    ft.Container(height=32),
                    self.progress_bar,
                    ft.Container(height=8),
                    self.progress_text,
                    ft.Container(height=8),
                    self.stats_text,
                    ft.Container(height=32),
                    ft.OutlinedButton(
                        "Cancel",
                        icon=ft.Icons.CANCEL,
                        on_click=self._cancel_scan,
                    ),
                ],
                horizontal_alignment=ft.CrossAxisAlignment.CENTER,
                alignment=ft.MainAxisAlignment.CENTER,
            ),
            padding=32,
            expand=True,
            alignment=ft.Alignment(0, 0),
        )
