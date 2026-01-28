"""Results display screen for ComPlexionist GUI."""

from __future__ import annotations

from collections.abc import Callable
from typing import TYPE_CHECKING

import flet as ft

from complexionist.config import add_ignored_collection, add_ignored_show
from complexionist.gui.screens.base import BaseScreen
from complexionist.gui.theme import PLEX_GOLD
from complexionist.statistics import calculate_movie_score, calculate_tv_score

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
        # References to ListView controls for updating on search
        self.movie_list_view: ft.ListView | None = None
        self.tv_list_view: ft.ListView | None = None
        # References to summary text controls for dynamic updates
        self.movie_gaps_count_text: ft.Text | None = None
        self.movie_score_text: ft.Text | None = None
        self.tv_gaps_count_text: ft.Text | None = None
        self.tv_missing_count_text: ft.Text | None = None
        self.tv_score_text: ft.Text | None = None

    def _create_stats_line(self) -> ft.Control | None:
        """Create compact stats line showing scan performance metrics."""
        stats = self.state.scan_stats
        if stats is None:
            return None

        # Build compact pipe-separated stats line matching CLI format
        # Time | Plex | TMDB | TVDB | Cache
        cache_color = ft.Colors.GREEN if stats.cache_hit_rate > 50 else ft.Colors.ORANGE
        parts: list[ft.Control] = [
            ft.Text(f"Time: {stats.duration_str}", size=12, color=ft.Colors.GREY_400),
        ]

        # Only show non-zero counts (matching CLI format)
        if stats.plex_calls > 0:
            parts.append(ft.Text(" | ", size=12, color=ft.Colors.GREY_600))
            parts.append(ft.Text(f"Plex: {stats.plex_calls}", size=12, color=ft.Colors.GREY_400))
        if stats.tmdb_calls > 0:
            parts.append(ft.Text(" | ", size=12, color=ft.Colors.GREY_600))
            parts.append(ft.Text(f"TMDB: {stats.tmdb_calls}", size=12, color=ft.Colors.GREY_400))
        if stats.tvdb_calls > 0:
            parts.append(ft.Text(" | ", size=12, color=ft.Colors.GREY_600))
            parts.append(ft.Text(f"TVDB: {stats.tvdb_calls}", size=12, color=ft.Colors.GREY_400))

        # Always show cache if there were any lookups
        if stats.cache_hits + stats.cache_misses > 0:
            parts.append(ft.Text(" | ", size=12, color=ft.Colors.GREY_600))
            parts.append(ft.Text(f"Cache: {stats.cache_hit_rate:.0f}%", size=12, color=cache_color))

        return ft.Row(parts, alignment=ft.MainAxisAlignment.CENTER)

    def _get_score_color(self, score: float) -> str:
        """Get the color for a score percentage."""
        if score >= 90:
            return ft.Colors.GREEN
        elif score >= 70:
            return ft.Colors.ORANGE
        return ft.Colors.RED

    def _ignore_collection(self, collection_id: int, collection_name: str) -> None:
        """Add a collection to the ignore list and remove from results."""
        # 1. Immediately remove from UI for instant feedback
        if self.movie_list_view:
            self.movie_list_view.controls = [
                c for c in self.movie_list_view.controls
                if getattr(c, "data", None) != collection_id
            ]

        # 2. Show snackbar and update page immediately (user sees item gone)
        snack = ft.SnackBar(
            content=ft.Text(f"'{collection_name}' added to ignore list"),
            bgcolor=ft.Colors.ORANGE,
            duration=4000,
        )
        self.page.overlay.append(snack)
        snack.open = True
        self.page.update()

        # 3. Now do slower operations (config save)
        add_ignored_collection(collection_id)
        self.state.ignored_collection_names[collection_id] = collection_name

        # 4. Update state and summary stats
        if self.state.movie_report:
            self.state.movie_report.collections_with_gaps = [
                c
                for c in self.state.movie_report.collections_with_gaps
                if c.collection_id != collection_id
            ]

            if self.movie_gaps_count_text:
                gaps_count = len(self.state.movie_report.collections_with_gaps)
                self.movie_gaps_count_text.value = str(gaps_count)
                self.movie_gaps_count_text.color = PLEX_GOLD if gaps_count > 0 else None

            if self.movie_score_text:
                total_owned = sum(
                    c.owned_movies for c in self.state.movie_report.collections_with_gaps
                )
                total_missing = sum(
                    c.missing_count for c in self.state.movie_report.collections_with_gaps
                )
                score = calculate_movie_score(total_owned, total_missing)
                self.movie_score_text.value = f"{score:.0f}%"
                self.movie_score_text.color = self._get_score_color(score)

            # 5. Update stats display
            self.page.update()

    def _ignore_show(self, tvdb_id: int, show_title: str) -> None:
        """Add a show to the ignore list and remove from results."""
        # 1. Immediately remove from UI for instant feedback
        if self.tv_list_view:
            self.tv_list_view.controls = [
                c for c in self.tv_list_view.controls
                if getattr(c, "data", None) != tvdb_id
            ]

        # 2. Show snackbar and update page immediately (user sees item gone)
        snack = ft.SnackBar(
            content=ft.Text(f"'{show_title}' added to ignore list"),
            bgcolor=ft.Colors.ORANGE,
            duration=4000,
        )
        self.page.overlay.append(snack)
        snack.open = True
        self.page.update()

        # 3. Now do slower operations (config save)
        add_ignored_show(tvdb_id)
        self.state.ignored_show_names[tvdb_id] = show_title

        # 4. Update state and summary stats
        if self.state.tv_report:
            self.state.tv_report.shows_with_gaps = [
                s for s in self.state.tv_report.shows_with_gaps if s.tvdb_id != tvdb_id
            ]

            if self.tv_gaps_count_text:
                gaps_count = len(self.state.tv_report.shows_with_gaps)
                self.tv_gaps_count_text.value = str(gaps_count)
                self.tv_gaps_count_text.color = PLEX_GOLD if gaps_count > 0 else None

            if self.tv_missing_count_text:
                missing_count = self.state.tv_report.total_missing
                self.tv_missing_count_text.value = str(missing_count)
                self.tv_missing_count_text.color = PLEX_GOLD if missing_count > 0 else None

            if self.tv_score_text:
                score = calculate_tv_score(self.state.tv_report.shows_with_gaps)
                self.tv_score_text.value = f"{score:.0f}%"
                self.tv_score_text.color = self._get_score_color(score)

            # 5. Update stats display
            self.page.update()

    def _build_movie_items(self) -> list[ft.Control]:
        """Build the list of movie collection items, filtered by search."""
        report = self.state.movie_report
        if report is None or not report.collections_with_gaps:
            return [
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

        items: list[ft.Control] = []
        for collection in report.collections_with_gaps:
            # Filter by search query (collection name OR any movie titles)
            if self.search_query:
                query_lower = self.search_query.lower()
                name_match = query_lower in collection.collection_name.lower()
                missing_match = any(
                    query_lower in m.title.lower() for m in collection.missing_movies
                )
                owned_match = any(
                    query_lower in m.title.lower() for m in collection.owned_movie_list
                )
                if not name_match and not missing_match and not owned_match:
                    continue

            # Build movie lists section
            movies_column_items: list[ft.Control] = []

            # Owned movies section (dimmed with checkmarks)
            if collection.owned_movie_list:
                for m in collection.owned_movie_list:
                    movies_column_items.append(
                        ft.TextButton(
                            content=ft.Row(
                                [
                                    ft.Icon(
                                        ft.Icons.CHECK,
                                        size=14,
                                        color=ft.Colors.GREEN_400,
                                    ),
                                    ft.Text(
                                        f"{m.title} ({m.year or '?'})",
                                        size=14,
                                        color=ft.Colors.GREY_500,
                                    ),
                                ],
                                spacing=4,
                            ),
                            url=m.tmdb_url,
                            style=ft.ButtonStyle(
                                padding=ft.padding.symmetric(horizontal=0, vertical=2),
                            ),
                        )
                    )

            # "Missing X" header
            movies_column_items.append(
                ft.Container(
                    content=ft.Text(
                        f"Missing {len(collection.missing_movies)}",
                        size=12,
                        weight=ft.FontWeight.BOLD,
                        color=PLEX_GOLD,
                    ),
                    padding=ft.padding.only(top=8, bottom=4),
                )
            )

            # Missing movies (with bullet points)
            for m in collection.missing_movies:
                movies_column_items.append(
                    ft.TextButton(
                        content=ft.Text(
                            f"• {m.title} ({m.year or 'TBA'})",
                            size=14,
                        ),
                        url=m.tmdb_url,
                        style=ft.ButtonStyle(
                            padding=ft.padding.symmetric(horizontal=0, vertical=2),
                        ),
                    )
                )

            movies_list = ft.Column(movies_column_items, spacing=0)

            # Build expanded content with poster and movie list
            poster_widget: ft.Control | None = None
            if collection.poster_url:
                poster_widget = ft.Container(
                    content=ft.Image(
                        src=collection.poster_url,
                        width=92,
                        height=138,
                        fit=ft.BoxFit.COVER,
                        border_radius=ft.border_radius.all(4),
                    ),
                    url=collection.tmdb_url,
                    tooltip=f"View {collection.collection_name} on TMDB",
                    ink=True,
                )

            # Content row with optional poster
            if poster_widget:
                content_row = ft.Row(
                    [
                        poster_widget,
                        ft.Container(width=16),
                        ft.Container(content=movies_list, expand=True),
                    ],
                    vertical_alignment=ft.CrossAxisAlignment.START,
                )
            else:
                content_row = movies_list

            # Create ignore button with closure to capture current collection
            def make_ignore_handler(
                coll_id: int, coll_name: str
            ) -> Callable[[ft.ControlEvent], None]:
                def handler(e: ft.ControlEvent) -> None:
                    self._ignore_collection(coll_id, coll_name)

                return handler

            ignore_btn = ft.IconButton(
                icon=ft.Icons.VISIBILITY_OFF,
                tooltip="Ignore this collection",
                icon_size=18,
                icon_color=ft.Colors.GREY_500,
                on_click=make_ignore_handler(collection.collection_id, collection.collection_name),
            )

            # Trailing row with ignore button and expand chevron
            trailing_row = ft.Row(
                [
                    ignore_btn,
                    ft.Icon(ft.Icons.EXPAND_MORE, color=ft.Colors.GREY_500),
                ],
                spacing=0,
                tight=True,
            )

            # Clickable title that opens TMDB (left-aligned)
            title_button = ft.Container(
                content=ft.TextButton(
                    content=ft.Text(collection.collection_name, size=16),
                    url=collection.tmdb_url,
                    tooltip=f"View {collection.collection_name} on TMDB",
                    style=ft.ButtonStyle(
                        padding=ft.padding.all(0),
                    ),
                ),
                alignment=ft.Alignment(-1, 0),
            )

            items.append(
                ft.ExpansionTile(
                    title=title_button,
                    subtitle=ft.Text(
                        f"Missing {len(collection.missing_movies)} of {collection.total_movies}",
                        color=ft.Colors.GREY_400,
                    ),
                    trailing=trailing_row,
                    controls=[
                        ft.Container(
                            content=content_row,
                            padding=ft.padding.only(left=16, bottom=16, right=16),
                        )
                    ],
                    controls_padding=ft.padding.all(0),
                    shape=ft.RoundedRectangleBorder(radius=0),
                    collapsed_shape=ft.RoundedRectangleBorder(radius=0),
                    data=collection.collection_id,  # Tag for instant removal
                )
            )

        # Show "no matches" if search filtered everything out
        if not items:
            return [
                ft.Container(
                    content=ft.Text(
                        f"No collections match '{self.search_query}'",
                        color=ft.Colors.GREY_400,
                    ),
                    padding=32,
                    alignment=ft.Alignment(0, 0),
                )
            ]

        return items

    def _create_movie_results(self) -> ft.Control:
        """Create movie results display."""
        report = self.state.movie_report
        if report is None:
            return ft.Text("No movie results available")

        # Calculate collection completion score
        total_owned = sum(c.owned_movies for c in report.collections_with_gaps)
        total_missing = sum(c.missing_count for c in report.collections_with_gaps)
        score = calculate_movie_score(total_owned, total_missing)
        score_color = self._get_score_color(score)

        # Create dynamic text controls and store references
        self.movie_gaps_count_text = ft.Text(
            str(len(report.collections_with_gaps)),
            size=24,
            weight=ft.FontWeight.BOLD,
            color=PLEX_GOLD if report.collections_with_gaps else None,
        )
        self.movie_score_text = ft.Text(
            f"{score:.0f}%",
            size=24,
            weight=ft.FontWeight.BOLD,
            color=score_color,
        )

        # Summary card
        summary = ft.Card(
            content=ft.Container(
                content=ft.Row(
                    [
                        ft.Column(
                            [
                                ft.Text("Movies Scanned", size=12, color=ft.Colors.GREY_400),
                                ft.Text(
                                    str(report.total_movies_scanned),
                                    size=24,
                                    weight=ft.FontWeight.BOLD,
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
                                self.movie_gaps_count_text,
                            ],
                            horizontal_alignment=ft.CrossAxisAlignment.CENTER,
                        ),
                        ft.VerticalDivider(),
                        ft.Column(
                            [
                                ft.Text("Completion", size=12, color=ft.Colors.GREY_400),
                                self.movie_score_text,
                            ],
                            horizontal_alignment=ft.CrossAxisAlignment.CENTER,
                        ),
                    ],
                    alignment=ft.MainAxisAlignment.SPACE_EVENLY,
                ),
                padding=24,
            )
        )

        # Build column with summary, stats, and results
        column_items: list[ft.Control] = [summary]

        # Add compact stats line below summary
        stats_line = self._create_stats_line()
        if stats_line:
            column_items.append(ft.Container(content=stats_line, padding=8))

        column_items.append(ft.Container(height=8))

        # Create ListView and store reference for search updates
        self.movie_list_view = ft.ListView(
            controls=self._build_movie_items(),
            expand=True,
            spacing=0,
        )
        column_items.append(self.movie_list_view)

        return ft.Column(column_items, expand=True)

    def _build_tv_items(self) -> list[ft.Control]:
        """Build the list of TV show items, filtered by search."""
        report = self.state.tv_report
        if report is None or not report.shows_with_gaps:
            return [
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

        items: list[ft.Control] = []
        for show in report.shows_with_gaps:
            # Filter by search (show title OR any episode title)
            if self.search_query:
                query_lower = self.search_query.lower()
                title_match = query_lower in show.show_title.lower()
                episode_match = any(
                    ep.title and query_lower in ep.title.lower()
                    for season in show.seasons_with_gaps
                    for ep in season.missing_episodes
                )
                if not title_match and not episode_match:
                    continue

            # Build episode list organized by season
            # Group contiguous entirely-missing seasons for cleaner display
            episodes_column_items: list[ft.Control] = []

            # Separate seasons into entirely missing vs partially missing
            seasons = show.seasons_with_gaps
            i = 0
            while i < len(seasons):
                season = seasons[i]
                is_entirely_missing = season.missing_count == season.total_episodes

                if is_entirely_missing:
                    # Find contiguous entirely-missing seasons
                    group_seasons = [season]
                    total_missing_in_group = season.missing_count

                    # Look ahead for contiguous entirely-missing seasons
                    while i + 1 < len(seasons):
                        next_season = seasons[i + 1]
                        next_entirely_missing = (
                            next_season.missing_count == next_season.total_episodes
                        )
                        # Check if contiguous (season numbers are sequential)
                        is_contiguous = (
                            next_season.season_number == seasons[i].season_number + 1
                        )

                        if next_entirely_missing and is_contiguous:
                            i += 1
                            group_seasons.append(next_season)
                            total_missing_in_group += next_season.missing_count
                        else:
                            break

                    # Display the group
                    if len(group_seasons) == 1:
                        # Single entirely-missing season
                        label = f"Season {season.season_number}"
                    else:
                        # Multiple contiguous entirely-missing seasons
                        first_num = group_seasons[0].season_number
                        last_num = group_seasons[-1].season_number
                        label = f"Season {first_num} to Season {last_num}"

                    episodes_column_items.append(
                        ft.Container(
                            content=ft.Row(
                                [
                                    ft.Text(
                                        label,
                                        size=13,
                                        weight=ft.FontWeight.BOLD,
                                        color=PLEX_GOLD,
                                    ),
                                    ft.Text(
                                        f"(Missing {total_missing_in_group} of {total_missing_in_group})",
                                        size=12,
                                        color=ft.Colors.GREY_500,
                                    ),
                                ],
                                spacing=8,
                            ),
                            padding=ft.padding.only(top=8, bottom=4),
                        )
                    )
                else:
                    # Partially missing season - show episodes
                    season_total = season.total_episodes
                    season_missing = season.missing_count

                    episodes_column_items.append(
                        ft.Container(
                            content=ft.Row(
                                [
                                    ft.Text(
                                        f"Season {season.season_number}",
                                        size=13,
                                        weight=ft.FontWeight.BOLD,
                                        color=PLEX_GOLD,
                                    ),
                                    ft.Text(
                                        f"(Missing {season_missing} of {season_total})",
                                        size=12,
                                        color=ft.Colors.GREY_500,
                                    ),
                                ],
                                spacing=8,
                            ),
                            padding=ft.padding.only(top=8, bottom=4),
                        )
                    )

                    # Missing episodes for this season (limit to 10 for performance)
                    max_episodes_shown = 10
                    episodes_to_show = season.missing_episodes[:max_episodes_shown]
                    remaining_count = len(season.missing_episodes) - max_episodes_shown

                    for ep in episodes_to_show:
                        # Episode row with code, title, and air date
                        ep_text = ep.episode_code
                        if ep.title:
                            ep_text = f"{ep.episode_code} - {ep.title}"

                        episodes_column_items.append(
                            ft.Row(
                                [
                                    ft.Icon(
                                        ft.Icons.RADIO_BUTTON_UNCHECKED,
                                        size=14,
                                        color=PLEX_GOLD,
                                    ),
                                    ft.Text(
                                        ep_text,
                                        size=13,
                                        expand=True,
                                    ),
                                    ft.Text(
                                        ep.aired_str,
                                        size=12,
                                        color=ft.Colors.GREY_500,
                                    ),
                                ],
                                spacing=8,
                            )
                        )

                    # Show count of remaining episodes if truncated
                    if remaining_count > 0:
                        episodes_column_items.append(
                            ft.Text(
                                f"    ... and {remaining_count} more episodes",
                                size=12,
                                italic=True,
                                color=ft.Colors.GREY_500,
                            )
                        )

                i += 1

            episodes_list = ft.Column(episodes_column_items, spacing=2)

            # Show completion percentage in subtitle
            completion = show.completion_percent
            total_missing = show.missing_count

            # Create ignore button with closure to capture current show
            def make_ignore_handler(show_id: int, title: str) -> Callable[[ft.ControlEvent], None]:
                def handler(e: ft.ControlEvent) -> None:
                    self._ignore_show(show_id, title)

                return handler

            ignore_btn = ft.IconButton(
                icon=ft.Icons.VISIBILITY_OFF,
                tooltip="Ignore this show",
                icon_size=18,
                icon_color=ft.Colors.GREY_500,
                on_click=make_ignore_handler(show.tvdb_id, show.show_title),
            )

            # Trailing row with ignore button and expand chevron
            trailing_row = ft.Row(
                [
                    ignore_btn,
                    ft.Icon(ft.Icons.EXPAND_MORE, color=ft.Colors.GREY_500),
                ],
                spacing=0,
                tight=True,
            )

            # Clickable title that opens TVDB (left-aligned)
            title_button = ft.Container(
                content=ft.TextButton(
                    content=ft.Text(show.show_title, size=16),
                    url=show.tvdb_url,
                    tooltip=f"View {show.show_title} on TVDB",
                    style=ft.ButtonStyle(
                        padding=ft.padding.all(0),
                    ),
                ),
                alignment=ft.Alignment(-1, 0),
            )

            items.append(
                ft.ExpansionTile(
                    title=title_button,
                    subtitle=ft.Text(
                        f"{total_missing} missing · {completion:.0f}% complete",
                        color=ft.Colors.GREY_400,
                    ),
                    trailing=trailing_row,
                    controls=[
                        ft.Container(
                            content=episodes_list,
                            padding=ft.padding.only(left=16, bottom=16, right=16),
                        )
                    ],
                    controls_padding=ft.padding.all(0),
                    shape=ft.RoundedRectangleBorder(radius=0),
                    collapsed_shape=ft.RoundedRectangleBorder(radius=0),
                    data=show.tvdb_id,  # Tag for instant removal
                )
            )

        # Show "no matches" if search filtered everything out
        if not items:
            return [
                ft.Container(
                    content=ft.Text(
                        f"No shows match '{self.search_query}'",
                        color=ft.Colors.GREY_400,
                    ),
                    padding=32,
                    alignment=ft.Alignment(0, 0),
                )
            ]

        return items

    def _create_tv_results(self) -> ft.Control:
        """Create TV results display."""
        report = self.state.tv_report
        if report is None:
            return ft.Text("No TV results available")

        # Calculate episode completion score
        score = calculate_tv_score(report.shows_with_gaps)
        score_color = self._get_score_color(score)

        # Create dynamic text controls and store references
        self.tv_gaps_count_text = ft.Text(
            str(len(report.shows_with_gaps)),
            size=24,
            weight=ft.FontWeight.BOLD,
            color=PLEX_GOLD if report.shows_with_gaps else None,
        )
        self.tv_missing_count_text = ft.Text(
            str(report.total_missing),
            size=24,
            weight=ft.FontWeight.BOLD,
            color=PLEX_GOLD if report.total_missing else None,
        )
        self.tv_score_text = ft.Text(
            f"{score:.0f}%",
            size=24,
            weight=ft.FontWeight.BOLD,
            color=score_color,
        )

        # Summary card
        summary = ft.Card(
            content=ft.Container(
                content=ft.Row(
                    [
                        ft.Column(
                            [
                                ft.Text("Shows Scanned", size=12, color=ft.Colors.GREY_400),
                                ft.Text(
                                    str(report.total_shows_scanned),
                                    size=24,
                                    weight=ft.FontWeight.BOLD,
                                ),
                            ],
                            horizontal_alignment=ft.CrossAxisAlignment.CENTER,
                        ),
                        ft.VerticalDivider(),
                        ft.Column(
                            [
                                ft.Text("Shows with Gaps", size=12, color=ft.Colors.GREY_400),
                                self.tv_gaps_count_text,
                            ],
                            horizontal_alignment=ft.CrossAxisAlignment.CENTER,
                        ),
                        ft.VerticalDivider(),
                        ft.Column(
                            [
                                ft.Text("Missing Episodes", size=12, color=ft.Colors.GREY_400),
                                self.tv_missing_count_text,
                            ],
                            horizontal_alignment=ft.CrossAxisAlignment.CENTER,
                        ),
                        ft.VerticalDivider(),
                        ft.Column(
                            [
                                ft.Text("Completion", size=12, color=ft.Colors.GREY_400),
                                self.tv_score_text,
                            ],
                            horizontal_alignment=ft.CrossAxisAlignment.CENTER,
                        ),
                    ],
                    alignment=ft.MainAxisAlignment.SPACE_EVENLY,
                ),
                padding=24,
            )
        )

        # Build column with summary, stats, and results
        column_items: list[ft.Control] = [summary]

        # Add compact stats line below summary
        stats_line = self._create_stats_line()
        if stats_line:
            column_items.append(ft.Container(content=stats_line, padding=8))

        column_items.append(ft.Container(height=8))

        # Create ListView and store reference for search updates
        self.tv_list_view = ft.ListView(
            controls=self._build_tv_items(),
            expand=True,
            spacing=0,
        )
        column_items.append(self.tv_list_view)

        return ft.Column(column_items, expand=True)

    def _on_search(self, e: ft.ControlEvent) -> None:
        """Handle search input."""
        self.search_query = e.control.value or ""
        # Rebuild the filtered list items
        self._update_filtered_results()

    def _update_filtered_results(self) -> None:
        """Update the list views with filtered results based on search query."""
        if self.movie_list_view is not None:
            self.movie_list_view.controls = self._build_movie_items()
        if self.tv_list_view is not None:
            self.tv_list_view.controls = self._build_tv_items()
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

        # Build column contents
        column_controls: list[ft.Control] = [
            header,
            ft.Divider(),
            ft.Container(
                content=content,
                expand=True,
            ),
        ]

        return ft.Container(
            content=ft.Column(column_controls),
            padding=16,
            expand=True,
        )
