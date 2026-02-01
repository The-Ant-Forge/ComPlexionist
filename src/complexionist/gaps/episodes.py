"""Episode gap detection logic."""

import re
from collections.abc import Callable
from datetime import UTC, datetime, timedelta

from complexionist.gaps.models import (
    EpisodeGapReport,
    MissingEpisode,
    SeasonGap,
    ShowGap,
)
from complexionist.plex import PlexClient, PlexEpisode
from complexionist.tvdb import (
    TVDBClient,
    TVDBEpisode,
    TVDBError,
    TVDBNotFoundError,
    TVDBRateLimitError,
)
from complexionist.utils import retry_with_backoff

# Multi-episode filename patterns
# Examples: S02E01-02, S02E01-E02, S02E01E02, S02E01-E02-E03
MULTI_EPISODE_PATTERNS = [
    # S02E01-02 or S02E01-2 (dash with numbers)
    re.compile(r"S(\d+)E(\d+)-(\d+)", re.IGNORECASE),
    # S02E01-E02 (dash with E prefix)
    re.compile(r"S(\d+)E(\d+)-E(\d+)", re.IGNORECASE),
    # S02E01E02 (consecutive E numbers)
    re.compile(r"S(\d+)E(\d+)E(\d+)", re.IGNORECASE),
    # S02E01E02E03 (multiple consecutive)
    re.compile(r"S(\d+)E(\d+)(?:E(\d+))+", re.IGNORECASE),
]


def parse_multi_episode_filename(file_path: str | None) -> list[tuple[int, int]]:
    """Parse a filename for multi-episode ranges.

    Args:
        file_path: The file path to parse.

    Returns:
        List of (season, episode) tuples for all episodes in the file.
        Returns empty list if no multi-episode pattern is found.
    """
    if not file_path:
        return []

    episodes: list[tuple[int, int]] = []

    # Check each pattern
    for pattern in MULTI_EPISODE_PATTERNS:
        matches = pattern.findall(file_path)
        for match in matches:
            if len(match) >= 3:
                season = int(match[0])
                start_ep = int(match[1])
                end_ep = int(match[2])

                # Handle case where end episode is less (e.g., S02E01-2 means E01-E02)
                if end_ep < start_ep:
                    # Assume it's a shortened form (S02E10-12 means S02E10-E12)
                    pass  # Already handled below

                # Generate range
                for ep_num in range(start_ep, end_ep + 1):
                    if (season, ep_num) not in episodes:
                        episodes.append((season, ep_num))

    return episodes


class EpisodeGapFinder:
    """Find missing episodes from TV shows in a Plex library."""

    def __init__(
        self,
        plex_client: PlexClient,
        tvdb_client: TVDBClient,
        include_future: bool = False,
        include_specials: bool = False,
        recent_threshold_hours: int = 0,
        excluded_shows: list[str] | None = None,
        ignored_show_ids: list[int] | None = None,
        progress_callback: Callable[[str, int, int], None] | None = None,
    ) -> None:
        """Initialize the gap finder.

        Args:
            plex_client: Connected Plex client.
            tvdb_client: Configured TVDB client.
            include_future: Include unaired episodes in results.
            include_specials: Include Season 0 (specials) in results.
            recent_threshold_hours: Skip episodes aired within this many hours.
                Set to 0 to disable. Default is 0 (no threshold).
            excluded_shows: List of show titles to skip.
            ignored_show_ids: List of TVDB series IDs to skip.
            progress_callback: Optional callback for progress updates.
                Signature: (stage: str, current: int, total: int)
        """
        self.plex = plex_client
        self.tvdb = tvdb_client
        self.include_future = include_future
        self.include_specials = include_specials
        self.recent_threshold_hours = recent_threshold_hours
        self.excluded_shows = {s.lower() for s in (excluded_shows or [])}
        self.ignored_show_ids = set(ignored_show_ids or [])
        self._progress = progress_callback or (lambda *args: None)

    def find_gaps(self, library_name: str | None = None) -> EpisodeGapReport:
        """Find all missing episodes from TV shows.

        Args:
            library_name: Plex library name. If None, uses first TV library.

        Returns:
            Report with all episode gaps.
        """
        # Step 1: Get all shows from Plex
        self._progress("Loading TV library from Plex...", 0, 0)
        plex_shows = self.plex.get_shows(library_name, progress_callback=self._progress)

        # Determine library name for report
        if library_name is None:
            tv_libs = self.plex.get_tv_libraries()
            lib_name = tv_libs[0].title if tv_libs else "TV Shows"
        else:
            lib_name = library_name

        # Step 2: Filter shows with TVDB IDs and apply exclusions
        shows_with_tvdb = [
            s
            for s in plex_shows
            if s.has_tvdb_id
            and s.title.lower() not in self.excluded_shows
            and s.tvdb_id not in self.ignored_show_ids
        ]

        # Step 3: Process each show and find gaps
        show_gaps: list[ShowGap] = []
        total_episodes_owned = 0
        total = len(shows_with_tvdb)

        for i, show in enumerate(shows_with_tvdb):
            self._progress(f"Analyzing: {show.title}", i + 1, total)

            # Get episodes from Plex for this show
            plex_episodes = self.plex.get_episodes(show.rating_key)
            owned_episodes = self._build_owned_episode_set(plex_episodes)
            total_episodes_owned += len(owned_episodes)

            # Get first episode file path for folder navigation
            first_episode_path = next(
                (ep.file_path for ep in plex_episodes if ep.file_path),
                None,
            )

            # Get episodes and series info from TVDB
            try:
                tvdb_episodes = self._fetch_tvdb_episodes(show.tvdb_id)  # type: ignore[arg-type]
                # Get series info for poster
                series_info = self.tvdb.get_series(show.tvdb_id)  # type: ignore[arg-type]
                poster_url = series_info.image
            except TVDBNotFoundError:
                # Show not found on TVDB, skip
                continue
            except TVDBError as e:
                # Log API errors and continue with next show
                from complexionist.gui.errors import log_error

                log_error(e, f"TVDB API error for show: {show.title}")
                continue
            except Exception as e:
                # Log unexpected errors and continue
                from complexionist.gui.errors import log_error

                log_error(e, f"Unexpected error processing show: {show.title}")
                continue

            # Filter TVDB episodes
            tvdb_episodes = self._filter_tvdb_episodes(tvdb_episodes)

            # Find missing episodes
            gap = self._find_show_gaps(
                tvdb_id=show.tvdb_id,  # type: ignore[arg-type]
                show_title=show.title,
                owned_episodes=owned_episodes,
                tvdb_episodes=tvdb_episodes,
                poster_url=poster_url,
                first_episode_path=first_episode_path,
            )

            if gap and gap.missing_count > 0:
                show_gaps.append(gap)

        # Sort by missing count (most missing first)
        show_gaps.sort(key=lambda g: g.missing_count, reverse=True)

        return EpisodeGapReport(
            library_name=lib_name,
            total_shows_scanned=len(plex_shows),
            shows_with_tvdb_id=len(shows_with_tvdb),
            total_episodes_owned=total_episodes_owned,
            shows_with_gaps=show_gaps,
        )

    def _build_owned_episode_set(self, episodes: list[PlexEpisode]) -> set[tuple[int, int]]:
        """Build a set of owned episode identifiers.

        Handles multi-episode files by parsing filenames.

        Args:
            episodes: List of Plex episodes.

        Returns:
            Set of (season_number, episode_number) tuples.
        """
        owned: set[tuple[int, int]] = set()

        for ep in episodes:
            # Add the episode itself
            owned.add((ep.season_number, ep.episode_number))

            # Check for multi-episode files
            multi_eps = parse_multi_episode_filename(ep.file_path)
            for season, ep_num in multi_eps:
                owned.add((season, ep_num))

        return owned

    @retry_with_backoff(
        max_retries=3,
        base_delay=1.0,
        retry_on=(TVDBRateLimitError,),
    )
    def _fetch_tvdb_episodes(self, tvdb_id: int) -> list[TVDBEpisode]:
        """Fetch all episodes for a series from TVDB.

        Args:
            tvdb_id: TVDB series ID.

        Returns:
            List of TVDB episodes.
        """
        return self.tvdb.get_series_episodes(tvdb_id)

    def _filter_tvdb_episodes(self, episodes: list[TVDBEpisode]) -> list[TVDBEpisode]:
        """Filter TVDB episodes based on settings.

        Args:
            episodes: All episodes from TVDB.

        Returns:
            Filtered list of episodes.
        """
        filtered = []

        # Calculate the recent threshold cutoff
        if self.recent_threshold_hours > 0:
            recent_cutoff = datetime.now(UTC) - timedelta(hours=self.recent_threshold_hours)
        else:
            recent_cutoff = None

        for ep in episodes:
            # Filter specials (Season 0)
            if not self.include_specials and ep.is_special:
                continue

            # Filter future episodes
            if not self.include_future and not ep.is_aired:
                continue

            # Filter very recent episodes (within threshold hours)
            if recent_cutoff is not None and ep.aired is not None:
                # Convert date to datetime for comparison
                ep_datetime = datetime(ep.aired.year, ep.aired.month, ep.aired.day, tzinfo=UTC)
                if ep_datetime > recent_cutoff:
                    continue

            filtered.append(ep)

        return filtered

    def _find_show_gaps(
        self,
        tvdb_id: int,
        show_title: str,
        owned_episodes: set[tuple[int, int]],
        tvdb_episodes: list[TVDBEpisode],
        poster_url: str | None = None,
        first_episode_path: str | None = None,
    ) -> ShowGap | None:
        """Find gaps for a single show.

        Args:
            tvdb_id: TVDB series ID.
            show_title: Show title for the report.
            owned_episodes: Set of owned (season, episode) tuples.
            tvdb_episodes: Expected episodes from TVDB.
            poster_url: Optional URL to the show poster image.
            first_episode_path: Path to the first owned episode file.

        Returns:
            ShowGap if there are missing episodes, None otherwise.
        """
        # Group TVDB episodes by season
        seasons: dict[int, list[TVDBEpisode]] = {}
        for ep in tvdb_episodes:
            if ep.season_number not in seasons:
                seasons[ep.season_number] = []
            seasons[ep.season_number].append(ep)

        # Find missing episodes per season
        seasons_with_gaps: list[SeasonGap] = []
        total_expected = len(tvdb_episodes)
        total_owned = 0

        for season_num in sorted(seasons.keys()):
            season_eps = seasons[season_num]
            season_owned = 0
            missing_in_season: list[MissingEpisode] = []

            for tvdb_ep in season_eps:
                key = (tvdb_ep.season_number, tvdb_ep.episode_number)
                if key in owned_episodes:
                    season_owned += 1
                    total_owned += 1
                else:
                    missing_in_season.append(
                        MissingEpisode(
                            tvdb_id=tvdb_ep.id,
                            season_number=tvdb_ep.season_number,
                            episode_number=tvdb_ep.episode_number,
                            title=tvdb_ep.name,
                            aired=tvdb_ep.aired,
                            overview=tvdb_ep.overview or "",
                        )
                    )

            if missing_in_season:
                # Sort by episode number
                missing_in_season.sort(key=lambda e: e.episode_number)
                seasons_with_gaps.append(
                    SeasonGap(
                        season_number=season_num,
                        total_episodes=len(season_eps),
                        owned_episodes=season_owned,
                        missing_episodes=missing_in_season,
                    )
                )

        if not seasons_with_gaps:
            return None

        return ShowGap(
            tvdb_id=tvdb_id,
            show_title=show_title,
            total_episodes=total_expected,
            owned_episodes=total_owned,
            poster_url=poster_url,
            first_episode_path=first_episode_path,
            seasons_with_gaps=seasons_with_gaps,
        )
