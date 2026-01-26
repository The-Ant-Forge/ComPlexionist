"""Output formatting for gap reports.

Provides unified output handling for movie and TV gap reports
in text, JSON, and CSV formats.
"""

from __future__ import annotations

import csv
import io
import json
from abc import ABC, abstractmethod
from datetime import date
from pathlib import Path
from typing import TYPE_CHECKING

from rich.console import Console

if TYPE_CHECKING:
    from complexionist.gaps.models import EpisodeGapReport, MovieGapReport
    from complexionist.statistics import ScanStatistics


console = Console()


class ReportFormatter(ABC):
    """Abstract base class for report formatting."""

    @abstractmethod
    def to_json(self) -> str:
        """Convert report to JSON string."""
        pass

    @abstractmethod
    def to_csv(self) -> str:
        """Convert report to CSV string."""
        pass

    @abstractmethod
    def to_text(self, verbose: bool = False) -> None:
        """Output report as formatted text to console."""
        pass

    @abstractmethod
    def save_csv(self) -> Path:
        """Save report as CSV file and return path."""
        pass

    @abstractmethod
    def show_summary(
        self,
        stats: ScanStatistics,
        csv_path: Path | None = None,
    ) -> None:
        """Display summary report to console."""
        pass

    @staticmethod
    def _sanitize_filename(name: str) -> str:
        """Sanitize a string for use in a filename."""
        safe = "".join(c if c.isalnum() or c in " -_" else "_" for c in name)
        return safe.replace(" ", "_")

    @staticmethod
    def _get_score_color(score: float) -> str:
        """Get color for score display."""
        if score >= 90:
            return "green"
        elif score >= 70:
            return "yellow"
        return "red"

    @staticmethod
    def _format_api_stats(stats: ScanStatistics, api_type: str) -> str:
        """Format API call statistics as a summary line.

        Args:
            stats: Scan statistics.
            api_type: Either 'tmdb' or 'tvdb' for the external API.

        Returns:
            Formatted string like "Plex: 2 | TMDB: 15 | Cache: 85% hit rate"
        """
        parts = []
        if stats.plex_requests > 0:
            parts.append(f"Plex: {stats.plex_requests}")

        if api_type == "tmdb" and stats.total_tmdb_calls > 0:
            parts.append(f"TMDB: {stats.total_tmdb_calls}")
        elif api_type == "tvdb" and stats.total_tvdb_calls > 0:
            parts.append(f"TVDB: {stats.total_tvdb_calls}")

        total_cache = stats.cache_hits + stats.cache_misses
        if total_cache > 0:
            parts.append(f"Cache: {stats.cache_hit_rate:.0f}% hit rate")

        return " | ".join(parts) if parts else ""


class MovieReportFormatter(ReportFormatter):
    """Formatter for movie gap reports."""

    def __init__(self, report: MovieGapReport) -> None:
        self.report = report

    def to_json(self) -> str:
        """Convert movie gap report to JSON string."""
        output = {
            "library_name": self.report.library_name,
            "total_movies_scanned": self.report.total_movies_scanned,
            "movies_with_tmdb_id": self.report.movies_with_tmdb_id,
            "movies_in_collections": self.report.movies_in_collections,
            "unique_collections": self.report.unique_collections,
            "total_missing": self.report.total_missing,
            "collections": [
                {
                    "id": gap.collection_id,
                    "name": gap.collection_name,
                    "total": gap.total_movies,
                    "owned": gap.owned_movies,
                    "missing": [
                        {
                            "tmdb_id": m.tmdb_id,
                            "title": m.title,
                            "year": m.year,
                            "release_date": m.release_date.isoformat()
                            if m.release_date
                            else None,
                        }
                        for m in gap.missing_movies
                    ],
                }
                for gap in self.report.collections_with_gaps
            ],
        }
        return json.dumps(output, indent=2)

    def to_csv(self) -> str:
        """Convert movie gap report to CSV string."""
        output = io.StringIO()
        writer = csv.writer(output)
        writer.writerow(["Collection", "Movie Title", "Year", "TMDB ID", "Release Date"])

        for gap in self.report.collections_with_gaps:
            for movie in gap.missing_movies:
                writer.writerow(
                    [
                        gap.collection_name,
                        movie.title,
                        movie.year or "",
                        movie.tmdb_id,
                        movie.release_date.isoformat() if movie.release_date else "",
                    ]
                )

        return output.getvalue()

    def to_text(self, verbose: bool = False) -> None:
        """Output movie gap report as formatted text."""
        console.print()
        console.print(f"[bold blue]Movie Collection Gaps - {self.report.library_name}[/bold blue]")
        console.print()

        # Summary
        console.print(f"[dim]Movies scanned:[/dim] {self.report.total_movies_scanned}")
        console.print(f"[dim]With TMDB ID:[/dim] {self.report.movies_with_tmdb_id}")
        console.print(f"[dim]In collections:[/dim] {self.report.movies_in_collections}")
        console.print(f"[dim]Unique collections:[/dim] {self.report.unique_collections}")
        console.print()

        if not self.report.collections_with_gaps:
            console.print("[green]All collections are complete![/green]")
            return

        console.print(
            f"[yellow]Found {self.report.total_missing} missing movies in "
            f"{len(self.report.collections_with_gaps)} collections[/yellow]"
        )
        console.print()

        for gap in self.report.collections_with_gaps:
            console.print(
                f"[bold]{gap.collection_name}[/bold] "
                f"(missing {gap.missing_count} of {gap.total_movies})"
            )

            max_display = 5 if not verbose else len(gap.missing_movies)
            displayed = gap.missing_movies[:max_display]

            for movie in displayed:
                year_str = f" ({movie.year})" if movie.year else ""
                console.print(f"  - {movie.title}{year_str}")

            remaining = len(gap.missing_movies) - max_display
            if remaining > 0:
                console.print(f"  [dim]... and {remaining} more[/dim]")

            console.print()

    def save_csv(self) -> Path:
        """Save movie gap report as CSV file."""
        safe_name = self._sanitize_filename(self.report.library_name)
        filename = f"{safe_name}_movie_gaps_{date.today().isoformat()}.csv"
        filepath = Path.cwd() / filename

        with open(filepath, "w", newline="", encoding="utf-8") as f:
            f.write(self.to_csv())

        return filepath

    def show_summary(
        self,
        stats: ScanStatistics,
        csv_path: Path | None = None,
    ) -> None:
        """Display summary report for movie scan."""
        from datetime import datetime

        from rich.prompt import Confirm

        from complexionist.statistics import calculate_movie_score

        # Calculate score
        total_owned = sum(g.owned_movies for g in self.report.collections_with_gaps)
        total_missing = self.report.total_missing
        score = calculate_movie_score(total_owned, total_missing)

        # Report header
        console.print()
        console.print(
            f"[bold]Report:[/bold] {self.report.library_name} | "
            f"[bold]Movies[/bold] Scanner | {datetime.now().strftime('%Y-%m-%d %H:%M')}"
        )
        console.print()

        # Score
        score_color = self._get_score_color(score)
        console.print(
            f"[bold]Library Score:[/bold] [{score_color}]{score:.1f}%[/{score_color}] complete"
        )
        console.print()

        # Stats
        console.print(f"[dim]Collections analyzed:[/dim] {self.report.unique_collections}")
        console.print(f"[dim]Movies scanned:[/dim] {self.report.total_movies_scanned}")
        if self.report.collections_with_gaps:
            console.print(
                f"[dim]Collections with gaps:[/dim] {len(self.report.collections_with_gaps)}"
            )
            console.print(f"[dim]Missing movies:[/dim] {self.report.total_missing}")
        else:
            console.print("[green]All collections are complete![/green]")
        console.print()

        # Performance stats
        console.print(f"[dim]Time taken:[/dim] {stats._format_duration(stats.total_duration)}")

        api_stats = self._format_api_stats(stats, "tmdb")
        if api_stats:
            console.print(f"[dim]API calls:[/dim] {api_stats}")
        console.print()

        # CSV saved
        if csv_path:
            console.print(f"[green]CSV saved:[/green] {csv_path}")
            console.print()

        # Offer to show details
        if self.report.collections_with_gaps:
            if Confirm.ask("View missing movies list?", default=False):
                self.to_text(verbose=True)


class TVReportFormatter(ReportFormatter):
    """Formatter for TV episode gap reports."""

    def __init__(self, report: EpisodeGapReport) -> None:
        self.report = report

    def to_json(self) -> str:
        """Convert episode gap report to JSON string."""
        output = {
            "library_name": self.report.library_name,
            "total_shows_scanned": self.report.total_shows_scanned,
            "shows_with_tvdb_id": self.report.shows_with_tvdb_id,
            "total_episodes_owned": self.report.total_episodes_owned,
            "total_missing": self.report.total_missing,
            "shows": [
                {
                    "tvdb_id": show.tvdb_id,
                    "title": show.show_title,
                    "total_episodes": show.total_episodes,
                    "owned_episodes": show.owned_episodes,
                    "seasons": [
                        {
                            "season": season.season_number,
                            "total": season.total_episodes,
                            "owned": season.owned_episodes,
                            "missing": [
                                {
                                    "tvdb_id": ep.tvdb_id,
                                    "episode_code": ep.episode_code,
                                    "title": ep.title,
                                    "aired": ep.aired.isoformat() if ep.aired else None,
                                }
                                for ep in season.missing_episodes
                            ],
                        }
                        for season in show.seasons_with_gaps
                    ],
                }
                for show in self.report.shows_with_gaps
            ],
        }
        return json.dumps(output, indent=2)

    def to_csv(self) -> str:
        """Convert episode gap report to CSV string."""
        output = io.StringIO()
        writer = csv.writer(output)
        writer.writerow(["Show", "Season", "Episode", "Title", "TVDB ID", "Aired"])

        for show in self.report.shows_with_gaps:
            for season in show.seasons_with_gaps:
                for ep in season.missing_episodes:
                    writer.writerow(
                        [
                            show.show_title,
                            season.season_number,
                            ep.episode_code,
                            ep.title or "",
                            ep.tvdb_id,
                            ep.aired.isoformat() if ep.aired else "",
                        ]
                    )

        return output.getvalue()

    def to_text(self, verbose: bool = False) -> None:
        """Output episode gap report as formatted text."""
        console.print()
        console.print(f"[bold blue]TV Episode Gaps - {self.report.library_name}[/bold blue]")
        console.print()

        # Summary
        console.print(f"[dim]Shows scanned:[/dim] {self.report.total_shows_scanned}")
        console.print(f"[dim]With TVDB ID:[/dim] {self.report.shows_with_tvdb_id}")
        console.print(f"[dim]Episodes owned:[/dim] {self.report.total_episodes_owned}")
        console.print()

        if not self.report.shows_with_gaps:
            console.print("[green]All shows are complete![/green]")
            return

        console.print(
            f"[yellow]Found {self.report.total_missing} missing episodes in "
            f"{len(self.report.shows_with_gaps)} shows[/yellow]"
        )
        console.print()

        for show in self.report.shows_with_gaps:
            console.print(
                f"[bold]{show.show_title}[/bold] "
                f"({show.owned_episodes}/{show.total_episodes} - {show.completion_percent:.0f}%)"
            )

            for season in show.seasons_with_gaps:
                console.print(f"  [dim]Season {season.season_number}:[/dim]")

                max_display = 5 if not verbose else len(season.missing_episodes)
                displayed = season.missing_episodes[:max_display]

                for ep in displayed:
                    title_part = f" - {ep.title}" if ep.title else ""
                    console.print(f"    {ep.episode_code}{title_part}")

                remaining = len(season.missing_episodes) - max_display
                if remaining > 0:
                    console.print(f"    [dim]... and {remaining} more[/dim]")

            console.print()

    def save_csv(self) -> Path:
        """Save episode gap report as CSV file."""
        safe_name = self._sanitize_filename(self.report.library_name)
        filename = f"{safe_name}_tv_gaps_{date.today().isoformat()}.csv"
        filepath = Path.cwd() / filename

        with open(filepath, "w", newline="", encoding="utf-8") as f:
            f.write(self.to_csv())

        return filepath

    def show_summary(
        self,
        stats: ScanStatistics,
        csv_path: Path | None = None,
    ) -> None:
        """Display summary report for TV scan."""
        from datetime import datetime

        from rich.prompt import Confirm

        from complexionist.statistics import calculate_tv_score

        # Calculate score
        score = calculate_tv_score(self.report.shows_with_gaps)

        # Report header
        console.print()
        console.print(
            f"[bold]Report:[/bold] {self.report.library_name} | "
            f"[bold]TV[/bold] Scanner | {datetime.now().strftime('%Y-%m-%d %H:%M')}"
        )
        console.print()

        # Score
        score_color = self._get_score_color(score)
        console.print(
            f"[bold]Library Score:[/bold] [{score_color}]{score:.1f}%[/{score_color}] complete"
        )
        console.print()

        # Stats
        console.print(f"[dim]Shows analyzed:[/dim] {self.report.shows_with_tvdb_id}")
        console.print(f"[dim]Episodes owned:[/dim] {self.report.total_episodes_owned}")
        if self.report.shows_with_gaps:
            console.print(f"[dim]Shows with gaps:[/dim] {len(self.report.shows_with_gaps)}")
            console.print(f"[dim]Missing episodes:[/dim] {self.report.total_missing}")
            # Top 3 shows with most missing
            sorted_shows = sorted(
                self.report.shows_with_gaps, key=lambda s: s.missing_count, reverse=True
            )
            top_shows = sorted_shows[:3]
            top_shows_str = ", ".join(f"{s.show_title} ({s.missing_count})" for s in top_shows)
            console.print(f"[dim]Top gaps:[/dim] {top_shows_str}")
        else:
            console.print("[green]All shows are complete![/green]")
        console.print()

        # Performance stats
        console.print(f"[dim]Time taken:[/dim] {stats._format_duration(stats.total_duration)}")

        api_stats = self._format_api_stats(stats, "tvdb")
        if api_stats:
            console.print(f"[dim]API calls:[/dim] {api_stats}")
        console.print()

        # CSV saved
        if csv_path:
            console.print(f"[green]CSV saved:[/green] {csv_path}")
            console.print()

        # Offer to show details
        if self.report.shows_with_gaps:
            if Confirm.ask("View missing episodes list?", default=False):
                self.to_text(verbose=True)
