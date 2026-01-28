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
        # Live API stats line
        self.api_stats_text = ft.Text("", size=12, color=ft.Colors.GREY_500)

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
        from complexionist.statistics import ScanStatistics

        self.state.scan_progress.phase = phase
        self.state.scan_progress.current = current
        self.state.scan_progress.total = total

        # Update UI controls
        if total > 0:
            self.progress_bar.value = current / total
            self.progress_text.value = f"{current} / {total}"
            # Update stats text with percentage
            percent = (current / total) * 100
            self.stats_text.value = f"{percent:.0f}% complete"
        else:
            self.progress_bar.value = None  # Indeterminate
            self.progress_text.value = "Processing..."
            self.stats_text.value = ""

        self.phase_text.value = phase

        # Update live API stats (matching CLI format)
        stats = ScanStatistics.get_current()
        if stats:
            # Format elapsed time
            elapsed = stats.total_duration.total_seconds()
            if elapsed < 60:
                time_str = f"{elapsed:.1f}s"
            else:
                mins = int(elapsed // 60)
                secs = elapsed % 60
                time_str = f"{mins}m {secs:.0f}s"

            # Build stats parts matching CLI: Time | Plex | TMDB | TVDB | Cache
            parts = [f"Time: {time_str}"]
            if stats.plex_requests > 0:
                parts.append(f"Plex: {stats.plex_requests}")
            if stats.total_tmdb_calls > 0:
                parts.append(f"TMDB: {stats.total_tmdb_calls}")
            if stats.total_tvdb_calls > 0:
                parts.append(f"TVDB: {stats.total_tvdb_calls}")

            cache_total = stats.cache_hits + stats.cache_misses
            if cache_total > 0:
                hit_rate = (stats.cache_hits / cache_total) * 100
                parts.append(f"Cache: {hit_rate:.0f}%")

            self.api_stats_text.value = " | ".join(parts)

        # Update the page to reflect changes
        self.page.update()

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
                    ft.Container(height=4),
                    self.stats_text,
                    ft.Container(height=8),
                    self.api_stats_text,
                    ft.Container(height=24),
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
