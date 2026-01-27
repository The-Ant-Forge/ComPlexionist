"""Results display screen for ComPlexionist GUI."""

from __future__ import annotations

from collections.abc import Callable
from typing import TYPE_CHECKING

import flet as ft

from complexionist.gui.screens.base import BaseScreen
from complexionist.gui.theme import PLEX_GOLD

if TYPE_CHECKING:
    from complexionist.gui.state import AppState


class ResultsScreen(BaseScreen):
    """Results display screen showing gaps found."""

    def __init__(
        self,
        page: ft.Page,
        state: AppState,
        on_back: Callable[[], None],
        on_export: Callable[[str], None],
    ) -> None:
        """Initialize results screen.

        Args:
            page: Flet page instance.
            state: Application state.
            on_back: Callback to go back to dashboard.
            on_export: Callback to export results (format: csv, json, clipboard).
        """
        super().__init__(page, state)
        self.on_back = on_back
        self.on_export = on_export
        self.search_query = ""

    def _create_movie_results(self) -> ft.Control:
        """Create movie results display."""
        report = self.state.movie_report
        if report is None:
            return ft.Text("No movie results available")

        # Summary card
        summary = ft.Card(
            content=ft.Container(
                content=ft.Row(
                    [
                        ft.Column(
                            [
                                ft.Text("Movies Scanned", size=12, color=ft.Colors.GREY_400),
                                ft.Text(
                                    str(report.total_movies), size=24, weight=ft.FontWeight.BOLD
                                ),
                            ],
                            horizontal_alignment=ft.CrossAxisAlignment.CENTER,
                        ),
                        ft.VerticalDivider(),
                        ft.Column(
                            [
                                ft.Text("In Collections", size=12, color=ft.Colors.GREY_400),
                                ft.Text(
                                    str(report.movies_in_collections),
                                    size=24,
                                    weight=ft.FontWeight.BOLD,
                                ),
                            ],
                            horizontal_alignment=ft.CrossAxisAlignment.CENTER,
                        ),
                        ft.VerticalDivider(),
                        ft.Column(
                            [
                                ft.Text("Collections with Gaps", size=12, color=ft.Colors.GREY_400),
                                ft.Text(
                                    str(len(report.collections_with_gaps)),
                                    size=24,
                                    weight=ft.FontWeight.BOLD,
                                    color=PLEX_GOLD if report.collections_with_gaps else None,
                                ),
                            ],
                            horizontal_alignment=ft.CrossAxisAlignment.CENTER,
                        ),
                    ],
                    alignment=ft.MainAxisAlignment.SPACE_EVENLY,
                ),
                padding=24,
            )
        )

        # Collection list
        if not report.collections_with_gaps:
            items = [
                ft.Container(
                    content=ft.Column(
                        [
                            ft.Icon(ft.Icons.CHECK_CIRCLE, size=48, color=ft.Colors.GREEN),
                            ft.Text("No gaps found!", size=18),
                            ft.Text("All collections are complete.", color=ft.Colors.GREY_400),
                        ],
                        horizontal_alignment=ft.CrossAxisAlignment.CENTER,
                    ),
                    padding=32,
                    alignment=ft.Alignment(0, 0),
                )
            ]
        else:
            items = []
            for collection in report.collections_with_gaps:
                # Filter by search
                if (
                    self.search_query
                    and self.search_query.lower() not in collection.collection_name.lower()
                ):
                    continue

                missing_list = ft.Column(
                    [
                        ft.Text(
                            f"• {m.title} ({m.year or 'TBA'})",
                            size=14,
                        )
                        for m in collection.missing_movies
                    ],
                    spacing=4,
                )

                items.append(
                    ft.ExpansionTile(
                        title=ft.Text(collection.collection_name),
                        subtitle=ft.Text(
                            f"Missing {len(collection.missing_movies)} of {collection.total_in_collection}",
                            color=ft.Colors.GREY_400,
                        ),
                        controls=[
                            ft.Container(
                                content=missing_list,
                                padding=ft.padding.only(left=16, bottom=16),
                            )
                        ],
                    )
                )

        return ft.Column(
            [
                summary,
                ft.Container(height=16),
                ft.ListView(
                    controls=items,
                    expand=True,
                    spacing=8,
                ),
            ],
            expand=True,
        )

    def _create_tv_results(self) -> ft.Control:
        """Create TV results display."""
        report = self.state.tv_report
        if report is None:
            return ft.Text("No TV results available")

        # Summary card
        summary = ft.Card(
            content=ft.Container(
                content=ft.Row(
                    [
                        ft.Column(
                            [
                                ft.Text("Shows Scanned", size=12, color=ft.Colors.GREY_400),
                                ft.Text(
                                    str(report.total_shows), size=24, weight=ft.FontWeight.BOLD
                                ),
                            ],
                            horizontal_alignment=ft.CrossAxisAlignment.CENTER,
                        ),
                        ft.VerticalDivider(),
                        ft.Column(
                            [
                                ft.Text("Shows with Gaps", size=12, color=ft.Colors.GREY_400),
                                ft.Text(
                                    str(len(report.shows_with_gaps)),
                                    size=24,
                                    weight=ft.FontWeight.BOLD,
                                    color=PLEX_GOLD if report.shows_with_gaps else None,
                                ),
                            ],
                            horizontal_alignment=ft.CrossAxisAlignment.CENTER,
                        ),
                        ft.VerticalDivider(),
                        ft.Column(
                            [
                                ft.Text("Missing Episodes", size=12, color=ft.Colors.GREY_400),
                                ft.Text(
                                    str(report.total_missing_episodes),
                                    size=24,
                                    weight=ft.FontWeight.BOLD,
                                    color=PLEX_GOLD if report.total_missing_episodes else None,
                                ),
                            ],
                            horizontal_alignment=ft.CrossAxisAlignment.CENTER,
                        ),
                    ],
                    alignment=ft.MainAxisAlignment.SPACE_EVENLY,
                ),
                padding=24,
            )
        )

        # Show list
        if not report.shows_with_gaps:
            items = [
                ft.Container(
                    content=ft.Column(
                        [
                            ft.Icon(ft.Icons.CHECK_CIRCLE, size=48, color=ft.Colors.GREEN),
                            ft.Text("No gaps found!", size=18),
                            ft.Text("All episodes are present.", color=ft.Colors.GREY_400),
                        ],
                        horizontal_alignment=ft.CrossAxisAlignment.CENTER,
                    ),
                    padding=32,
                    alignment=ft.Alignment(0, 0),
                )
            ]
        else:
            items = []
            for show in report.shows_with_gaps:
                # Filter by search
                if self.search_query and self.search_query.lower() not in show.show_name.lower():
                    continue

                # Group by season
                seasons: dict[int, list[str]] = {}
                for ep in show.missing_episodes:
                    if ep.season_number not in seasons:
                        seasons[ep.season_number] = []
                    seasons[ep.season_number].append(f"E{ep.episode_number:02d}")

                season_text = ", ".join(
                    f"S{s:02d}: {', '.join(eps)}" for s, eps in sorted(seasons.items())
                )

                items.append(
                    ft.ExpansionTile(
                        title=ft.Text(show.show_name),
                        subtitle=ft.Text(
                            f"{len(show.missing_episodes)} missing episodes",
                            color=ft.Colors.GREY_400,
                        ),
                        controls=[
                            ft.Container(
                                content=ft.Text(season_text, size=14),
                                padding=ft.padding.only(left=16, bottom=16),
                            )
                        ],
                    )
                )

        return ft.Column(
            [
                summary,
                ft.Container(height=16),
                ft.ListView(
                    controls=items,
                    expand=True,
                    spacing=8,
                ),
            ],
            expand=True,
        )

    def _on_search(self, e: ft.ControlEvent) -> None:
        """Handle search input."""
        self.search_query = e.control.value or ""
        self.page.update()

    def build(self) -> ft.Control:
        """Build the results UI."""
        # Determine what to show based on scan type and available results
        has_movies = self.state.movie_report is not None
        has_tv = self.state.tv_report is not None

        # Header with export buttons
        header = ft.Row(
            [
                ft.IconButton(
                    icon=ft.Icons.ARROW_BACK,
                    on_click=lambda e: self.on_back(),
                ),
                ft.Text("Results", size=24, weight=ft.FontWeight.BOLD),
                ft.Container(expand=True),
                ft.TextField(
                    hint_text="Search...",
                    prefix_icon=ft.Icons.SEARCH,
                    on_change=self._on_search,
                    width=200,
                    height=40,
                    text_size=14,
                ),
                ft.PopupMenuButton(
                    icon=ft.Icons.DOWNLOAD,
                    items=[
                        ft.PopupMenuItem(
                            content=ft.Row([ft.Icon(ft.Icons.TABLE_CHART), ft.Text("Export CSV")]),
                            on_click=lambda e: self.on_export("csv"),
                        ),
                        ft.PopupMenuItem(
                            content=ft.Row([ft.Icon(ft.Icons.DATA_OBJECT), ft.Text("Export JSON")]),
                            on_click=lambda e: self.on_export("json"),
                        ),
                        ft.PopupMenuItem(
                            content=ft.Row([ft.Icon(ft.Icons.COPY), ft.Text("Copy to Clipboard")]),
                            on_click=lambda e: self.on_export("clipboard"),
                        ),
                    ],
                ),
            ],
            alignment=ft.MainAxisAlignment.START,
        )

        # Content tabs if both results exist
        if has_movies and has_tv:
            content = ft.Tabs(
                tabs=[
                    ft.Tab(
                        text="Movies",
                        icon=ft.Icons.MOVIE_OUTLINED,
                        content=ft.Container(
                            content=self._create_movie_results(),
                            padding=16,
                        ),
                    ),
                    ft.Tab(
                        text="TV Shows",
                        icon=ft.Icons.TV_OUTLINED,
                        content=ft.Container(
                            content=self._create_tv_results(),
                            padding=16,
                        ),
                    ),
                ],
                expand=True,
            )
        elif has_movies:
            content = self._create_movie_results()
        elif has_tv:
            content = self._create_tv_results()
        else:
            content = ft.Text("No results to display")

        return ft.Container(
            content=ft.Column(
                [
                    header,
                    ft.Divider(),
                    ft.Container(
                        content=content,
                        expand=True,
                    ),
                ],
            ),
            padding=16,
            expand=True,
        )
