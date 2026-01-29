"""Statistics tracking for scan operations.

Tracks API calls, cache hits/misses, and timing information
to provide useful summaries after scans.
"""

from __future__ import annotations

import time
from dataclasses import dataclass, field
from datetime import timedelta
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from rich.console import Console


@dataclass
class PhaseStats:
    """Statistics for a single scan phase."""

    name: str
    started_at: float = 0.0
    ended_at: float = 0.0
    item_count: int = 0

    @property
    def duration(self) -> timedelta:
        """Get the duration of this phase."""
        if self.ended_at == 0:
            return timedelta(seconds=time.time() - self.started_at)
        return timedelta(seconds=self.ended_at - self.started_at)

    @property
    def duration_seconds(self) -> float:
        """Get the duration in seconds."""
        return self.duration.total_seconds()


@dataclass
class ScanStatistics:
    """Statistics for a full scan operation.

    Use as a context manager or track manually:

        stats = ScanStatistics()
        stats.start_phase("Fetching movies")
        # ... do work ...
        stats.end_phase(item_count=100)
        stats.record_api_call("tmdb_movie")
        stats.print_summary(console)
    """

    # API call counts
    plex_requests: int = 0
    tmdb_movie_requests: int = 0
    tmdb_collection_requests: int = 0
    tvdb_series_requests: int = 0
    tvdb_episode_requests: int = 0

    # Cache statistics (separate for TMDB and TVDB)
    cache_hits: int = 0
    cache_misses: int = 0
    cache_hits_tmdb: int = 0
    cache_misses_tmdb: int = 0
    cache_hits_tvdb: int = 0
    cache_misses_tvdb: int = 0

    # Phase tracking
    phases: list[PhaseStats] = field(default_factory=list)
    _current_phase: PhaseStats | None = field(default=None, repr=False)

    # Overall timing
    _started_at: float = field(default=0.0, repr=False)
    _ended_at: float = field(default=0.0, repr=False)

    # Global instance for easy access
    _instance: ScanStatistics | None = field(default=None, repr=False)

    def start(self) -> None:
        """Start tracking the scan."""
        self._started_at = time.time()
        ScanStatistics._instance = self

    def stop(self) -> None:
        """Stop tracking the scan."""
        self._ended_at = time.time()
        if self._current_phase:
            self.end_phase()

    @classmethod
    def get_current(cls) -> ScanStatistics | None:
        """Get the current active statistics instance."""
        return cls._instance

    @classmethod
    def reset_current(cls) -> None:
        """Reset the current statistics instance."""
        cls._instance = None

    @property
    def total_duration(self) -> timedelta:
        """Get the total duration of the scan."""
        if self._started_at == 0:
            return timedelta(0)
        end = self._ended_at if self._ended_at > 0 else time.time()
        return timedelta(seconds=end - self._started_at)

    @property
    def total_api_calls(self) -> int:
        """Get the total number of external API calls (TMDB + TVDB)."""
        return (
            self.tmdb_movie_requests
            + self.tmdb_collection_requests
            + self.tvdb_series_requests
            + self.tvdb_episode_requests
        )

    @property
    def total_tmdb_calls(self) -> int:
        """Get the total number of TMDB API calls."""
        return self.tmdb_movie_requests + self.tmdb_collection_requests

    @property
    def total_tvdb_calls(self) -> int:
        """Get the total number of TVDB API calls."""
        return self.tvdb_series_requests + self.tvdb_episode_requests

    @property
    def cache_hit_rate(self) -> float:
        """Get the cache hit rate as a percentage."""
        total = self.cache_hits + self.cache_misses
        if total == 0:
            return 0.0
        return (self.cache_hits / total) * 100

    @property
    def cache_hit_rate_tmdb(self) -> float:
        """Get the TMDB cache hit rate as a percentage."""
        total = self.cache_hits_tmdb + self.cache_misses_tmdb
        if total == 0:
            return 0.0
        return (self.cache_hits_tmdb / total) * 100

    @property
    def cache_hit_rate_tvdb(self) -> float:
        """Get the TVDB cache hit rate as a percentage."""
        total = self.cache_hits_tvdb + self.cache_misses_tvdb
        if total == 0:
            return 0.0
        return (self.cache_hits_tvdb / total) * 100

    def start_phase(self, name: str) -> None:
        """Start a new phase.

        Args:
            name: Name of the phase (e.g., "Fetching movies").
        """
        if self._current_phase:
            self.end_phase()
        self._current_phase = PhaseStats(name=name, started_at=time.time())

    def end_phase(self, item_count: int = 0) -> None:
        """End the current phase.

        Args:
            item_count: Number of items processed in this phase.
        """
        if self._current_phase:
            self._current_phase.ended_at = time.time()
            self._current_phase.item_count = item_count
            self.phases.append(self._current_phase)
            self._current_phase = None

    def record_api_call(self, call_type: str) -> None:
        """Record an API call.

        Args:
            call_type: Type of call (plex, tmdb_movie, tmdb_collection,
                       tvdb_series, tvdb_episode).
        """
        if call_type == "plex":
            self.plex_requests += 1
        elif call_type == "tmdb_movie":
            self.tmdb_movie_requests += 1
        elif call_type == "tmdb_collection":
            self.tmdb_collection_requests += 1
        elif call_type == "tvdb_series":
            self.tvdb_series_requests += 1
        elif call_type == "tvdb_episode":
            self.tvdb_episode_requests += 1

    def record_cache_hit(self, api: str = "") -> None:
        """Record a cache hit.

        Args:
            api: Optional API identifier ("tmdb" or "tvdb") for separate tracking.
        """
        self.cache_hits += 1
        if api == "tmdb":
            self.cache_hits_tmdb += 1
        elif api == "tvdb":
            self.cache_hits_tvdb += 1

    def record_cache_miss(self, api: str = "") -> None:
        """Record a cache miss.

        Args:
            api: Optional API identifier ("tmdb" or "tvdb") for separate tracking.
        """
        self.cache_misses += 1
        if api == "tmdb":
            self.cache_misses_tmdb += 1
        elif api == "tvdb":
            self.cache_misses_tvdb += 1

    def _format_duration(self, td: timedelta) -> str:
        """Format a timedelta for display."""
        total_seconds = td.total_seconds()
        if total_seconds < 60:
            return f"{total_seconds:.1f}s"
        minutes = int(total_seconds // 60)
        seconds = total_seconds % 60
        return f"{minutes}m {seconds:.1f}s"

    def print_summary(self, console: Console) -> None:
        """Print a summary of statistics to the console.

        Args:
            console: Rich console for output.
        """
        console.print()
        console.print("[bold]Scan Summary[/bold]")
        console.print()

        # Phase timing
        if self.phases:
            console.print("[dim]Phases:[/dim]")
            for phase in self.phases:
                duration_str = self._format_duration(phase.duration)
                if phase.item_count > 0:
                    console.print(f"  {phase.name}: {phase.item_count} items ({duration_str})")
                else:
                    console.print(f"  {phase.name}: {duration_str}")

        # Total duration
        console.print()
        console.print(f"[bold]Total time:[/bold] {self._format_duration(self.total_duration)}")

        # API calls
        if self.total_api_calls > 0:
            console.print(f"[bold]API calls:[/bold] {self.total_api_calls}")
            if self.tmdb_movie_requests > 0:
                console.print(f"  TMDB movies: {self.tmdb_movie_requests}")
            if self.tmdb_collection_requests > 0:
                console.print(f"  TMDB collections: {self.tmdb_collection_requests}")
            if self.tvdb_series_requests > 0:
                console.print(f"  TVDB series: {self.tvdb_series_requests}")
            if self.tvdb_episode_requests > 0:
                console.print(f"  TVDB episodes: {self.tvdb_episode_requests}")

        # Cache stats
        total_cache = self.cache_hits + self.cache_misses
        if total_cache > 0:
            console.print()
            console.print(
                f"[bold]Cache:[/bold] {self.cache_hit_rate:.0f}% hit rate "
                f"({self.cache_hits} hits, {self.cache_misses} misses)"
            )

    @property
    def api_calls_saved(self) -> int:
        """Number of API calls saved by cache hits."""
        return self.cache_hits


def calculate_movie_score(
    total_owned: int,
    total_missing: int,
) -> float:
    """Calculate overall completion score for movies.

    Args:
        total_owned: Total owned movies in collections with gaps.
        total_missing: Total missing movies.

    Returns:
        Completion percentage (0-100).
    """
    total = total_owned + total_missing
    if total == 0:
        return 100.0
    return (total_owned / total) * 100


def calculate_tv_score(shows_with_gaps: list) -> float:
    """Calculate overall completion score for TV shows.

    Args:
        shows_with_gaps: List of ShowGap objects.

    Returns:
        Completion percentage (0-100).
    """
    total_episodes = 0
    owned_episodes = 0

    for show in shows_with_gaps:
        total_episodes += show.total_episodes
        owned_episodes += show.owned_episodes

    if total_episodes == 0:
        return 100.0

    return (owned_episodes / total_episodes) * 100
