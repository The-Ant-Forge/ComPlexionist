"""Tests for the CLI module."""

import re
from collections.abc import Iterator
from datetime import date
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest
from click.testing import CliRunner

from complexionist import __version__
from complexionist.cli import main
from complexionist.config import reset_config
from complexionist.gaps import EpisodeGapReport, MovieGapReport
from complexionist.plex import PlexEpisode, PlexError, PlexMovie, PlexShow
from complexionist.tmdb import TMDBCollection, TMDBError, TMDBMovie, TMDBMovieDetails
from complexionist.tvdb import TVDBEpisode

VALID_INI = """\
[plex:0]
name = Test Server
url = http://localhost:32400
token = test-token-12345

[tmdb]
api_key = test-tmdb-key

[tvdb]
api_key = test-tvdb-key
"""


@pytest.fixture
def config_env(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Iterator[Path]:
    """Isolated cwd containing a valid INI; global config cache reset around the test."""
    (tmp_path / "complexionist.ini").write_text(VALID_INI, encoding="utf-8")
    monkeypatch.chdir(tmp_path)
    reset_config()
    yield tmp_path
    reset_config()


@pytest.fixture
def no_config_env(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Iterator[Path]:
    """Isolated cwd with no INI anywhere (home redirected so ~/.complexionist is empty)."""
    fake_home = tmp_path / "home"
    fake_home.mkdir()
    monkeypatch.setattr(Path, "home", classmethod(lambda cls: fake_home))
    work_dir = tmp_path / "work"
    work_dir.mkdir()
    monkeypatch.chdir(work_dir)
    reset_config()
    yield work_dir
    reset_config()


def _mock_plex_with_movies(movies: list[PlexMovie]) -> MagicMock:
    """Mock PlexClient exposing a single movie library."""
    client = MagicMock()
    client.get_movies.return_value = movies
    library = MagicMock(title="Movies", type="movie", locations=["/movies"])
    client.get_movie_libraries.return_value = [library]
    return client


def _mock_tmdb(
    movie_collections: dict[int, int | None],
    collections: dict[int, TMDBCollection],
) -> MagicMock:
    """Mock TMDBClient backed by static movie/collection data."""
    client = MagicMock()

    def get_movie(movie_id: int) -> TMDBMovieDetails:
        collection_id = movie_collections.get(movie_id)
        info = (
            {"id": collection_id, "name": f"Collection {collection_id}"} if collection_id else None
        )
        return TMDBMovieDetails(id=movie_id, title=f"Movie {movie_id}", belongs_to_collection=info)

    client.get_movie.side_effect = get_movie
    client.get_collection.side_effect = lambda cid: collections[cid]
    client.test_connection.return_value = True
    return client


def _movie_scan_mocks() -> tuple[MagicMock, MagicMock]:
    """Standard movie-scan scenario: 2 owned of 3 in one collection (1 missing)."""
    movies = [
        PlexMovie(rating_key="1", title="Movie A", tmdb_id=100),
        PlexMovie(rating_key="2", title="Movie B", tmdb_id=101),
    ]
    plex = _mock_plex_with_movies(movies)
    collections = {
        1: TMDBCollection(
            id=1,
            name="Alpha Collection",
            parts=[
                TMDBMovie(id=100, title="Movie A", release_date=date(2020, 1, 1)),
                TMDBMovie(id=101, title="Movie B", release_date=date(2020, 6, 1)),
                TMDBMovie(id=102, title="Missing Movie", release_date=date(2021, 1, 1)),
            ],
        ),
    }
    tmdb = _mock_tmdb({100: 1, 101: 1}, collections)
    return plex, tmdb


def _mock_plex_with_shows(
    shows: list[PlexShow], episodes_by_show: dict[str, list[PlexEpisode]]
) -> MagicMock:
    """Mock PlexClient exposing a single TV library."""
    client = MagicMock()
    client.get_shows.return_value = shows
    library = MagicMock(title="TV Shows", type="show", locations=["/tv"])
    client.get_tv_libraries.return_value = [library]
    client.get_episodes.side_effect = lambda rating_key: episodes_by_show.get(rating_key, [])
    return client


def _mock_tvdb(episodes_by_series: dict[int, list[TVDBEpisode]]) -> MagicMock:
    """Mock TVDBClient backed by static episode data."""
    client = MagicMock()
    client.get_series_episodes.side_effect = lambda series_id, series_status=None: (
        episodes_by_series.get(series_id, [])
    )
    series = MagicMock()
    series.image = "https://example.com/poster.jpg"
    series.status = "Continuing"
    client.get_series.return_value = series
    client.test_connection.return_value = True
    return client


def _tv_scan_mocks() -> tuple[MagicMock, MagicMock]:
    """Standard TV-scan scenario: 1 owned of 2 episodes (1 missing)."""
    shows = [PlexShow(rating_key="1", title="Test Show", tvdb_id=500)]
    episodes = {
        "1": [PlexEpisode(rating_key="e1", title="Pilot", season_number=1, episode_number=1)],
    }
    plex = _mock_plex_with_shows(shows, episodes)
    tvdb = _mock_tvdb(
        {
            500: [
                TVDBEpisode(id=1, seriesId=500, seasonNumber=1, number=1, aired=date(2020, 1, 1)),
                TVDBEpisode(
                    id=2,
                    seriesId=500,
                    seasonNumber=1,
                    number=2,
                    name="Second",
                    aired=date(2020, 1, 8),
                ),
            ]
        }
    )
    return plex, tvdb


def test_main_help() -> None:
    """Test that --help works."""
    runner = CliRunner()
    result = runner.invoke(main, ["--help"])
    assert result.exit_code == 0
    assert "ComPlexionist" in result.output


def test_version() -> None:
    """Test that --version works."""
    runner = CliRunner()
    result = runner.invoke(main, ["--version"])
    assert result.exit_code == 0
    # Version format: MAJOR.MINOR.PATCH (e.g., 1.1.47)
    assert re.search(r"\d+\.\d+\.\d+", result.output)
    assert __version__ in result.output


def test_movies_command_exists() -> None:
    """Test that the movies command exists."""
    runner = CliRunner()
    result = runner.invoke(main, ["movies", "--help"])
    assert result.exit_code == 0
    assert "missing movies" in result.output.lower()


def test_tv_command_exists() -> None:
    """Test that the tv command exists."""
    runner = CliRunner()
    result = runner.invoke(main, ["tv", "--help"])
    assert result.exit_code == 0
    assert "missing episodes" in result.output.lower()


def test_scan_command_exists() -> None:
    """Test that the scan command exists."""
    runner = CliRunner()
    result = runner.invoke(main, ["scan", "--help"])
    assert result.exit_code == 0
    assert "movie" in result.output.lower()


def test_config_path() -> None:
    """Test the config path command."""
    runner = CliRunner()
    result = runner.invoke(main, ["config", "path"])
    assert result.exit_code == 0
    assert ".complexionist" in result.output


class TestMoviesCommand:
    """Tests for the movies command with mocked API clients."""

    def test_happy_path_text_output(self, config_env: Path) -> None:
        """Full movie scan: text summary, missing count, and CSV file output."""
        plex, tmdb = _movie_scan_mocks()
        runner = CliRunner()

        with (
            patch("complexionist.plex.PlexClient", return_value=plex),
            patch("complexionist.tmdb.TMDBClient", return_value=tmdb),
        ):
            # "n" answers the "View missing movies list?" prompt
            result = runner.invoke(main, ["movies"], input="n\n")

        assert result.exit_code == 0
        assert "Library Score" in result.output
        assert "Missing movies: 1" in result.output
        # Default text mode also saves a CSV file into the working directory
        assert list(config_env.glob("*_movie_gaps_*.csv"))

    def test_json_format(self, config_env: Path) -> None:
        """--format json emits the JSON report (and no interactive prompt)."""
        plex, tmdb = _movie_scan_mocks()
        runner = CliRunner()

        with (
            patch("complexionist.plex.PlexClient", return_value=plex),
            patch("complexionist.tmdb.TMDBClient", return_value=tmdb),
        ):
            result = runner.invoke(main, ["movies", "--format", "json"])

        assert result.exit_code == 0
        assert '"library_name"' in result.output
        assert '"Missing Movie"' in result.output
        # JSON mode does not write a CSV file
        assert not list(config_env.glob("*_movie_gaps_*.csv"))

    def test_csv_format(self, config_env: Path) -> None:
        """--format csv emits CSV rows to stdout."""
        plex, tmdb = _movie_scan_mocks()
        runner = CliRunner()

        with (
            patch("complexionist.plex.PlexClient", return_value=plex),
            patch("complexionist.tmdb.TMDBClient", return_value=tmdb),
        ):
            result = runner.invoke(main, ["movies", "--format", "csv"])

        assert result.exit_code == 0
        assert "Collection,Movie Title,Year,TMDB ID" in result.output
        # Rich wraps long CSV rows at the console width; join lines before matching
        assert "Missing Movie" in result.output.replace("\n", "")

    def test_include_future_passed_to_finder(self, config_env: Path) -> None:
        """--include-future is forwarded to MovieGapFinder."""
        plex, _ = _movie_scan_mocks()
        finder_cls = MagicMock()
        finder_cls.return_value.find_gaps.return_value = MovieGapReport(
            library_name="Movies",
            total_movies_scanned=0,
            movies_with_tmdb_id=0,
            movies_in_collections=0,
            unique_collections=0,
        )
        runner = CliRunner()

        with (
            patch("complexionist.plex.PlexClient", return_value=plex),
            patch("complexionist.tmdb.TMDBClient", return_value=MagicMock()),
            patch("complexionist.gaps.MovieGapFinder", finder_cls),
        ):
            result = runner.invoke(main, ["movies", "--include-future"])

        assert result.exit_code == 0
        assert finder_cls.call_args.kwargs["include_future"] is True

    def test_plex_connection_failure_exits_nonzero(self, config_env: Path) -> None:
        """A Plex connection failure prints an error and exits 1."""
        plex = MagicMock()
        plex.connect.side_effect = PlexError("Connection refused")
        runner = CliRunner()

        with patch("complexionist.plex.PlexClient", return_value=plex):
            result = runner.invoke(main, ["movies"])

        assert result.exit_code == 1
        assert "Plex error" in result.output

    def test_tmdb_connection_failure_exits_nonzero(self, config_env: Path) -> None:
        """A TMDB connection failure prints an error and exits 1."""
        plex, _ = _movie_scan_mocks()
        tmdb = MagicMock()
        tmdb.test_connection.side_effect = TMDBError("Service unavailable")
        runner = CliRunner()

        with (
            patch("complexionist.plex.PlexClient", return_value=plex),
            patch("complexionist.tmdb.TMDBClient", return_value=tmdb),
        ):
            result = runner.invoke(main, ["movies"])

        assert result.exit_code == 1
        assert "TMDB error" in result.output

    def test_missing_config_declining_setup_exits_zero(self, no_config_env: Path) -> None:
        """With no config file the CLI offers the setup wizard.

        Current behavior note (review 2026-07 finding 32): declining the wizard
        prints "No configuration file found." and exits with code 0, not a
        non-zero error exit.
        """
        runner = CliRunner()
        # "n" declines the "Start setup?" prompt
        result = runner.invoke(main, ["movies"], input="n\n")

        assert result.exit_code == 0
        assert "No configuration file found" in result.output


class TestTVCommand:
    """Tests for the tv command with mocked API clients."""

    def test_happy_path_text_output(self, config_env: Path) -> None:
        """Full TV scan: text summary, missing count, and CSV file output."""
        plex, tvdb = _tv_scan_mocks()
        runner = CliRunner()

        with (
            patch("complexionist.plex.PlexClient", return_value=plex),
            patch("complexionist.tvdb.TVDBClient", return_value=tvdb),
        ):
            # "n" answers the "View missing episodes list?" prompt
            result = runner.invoke(main, ["tv"], input="n\n")

        assert result.exit_code == 0
        assert "Library Score" in result.output
        assert "Missing episodes: 1" in result.output
        assert list(config_env.glob("*_tv_gaps_*.csv"))

    def test_recent_threshold_zero_passed_to_finder(self, config_env: Path) -> None:
        """--recent-threshold 0 overrides the config default of 24."""
        plex, _ = _tv_scan_mocks()
        finder_cls = MagicMock()
        finder_cls.return_value.find_gaps.return_value = EpisodeGapReport(
            library_name="TV Shows",
            total_shows_scanned=0,
            shows_with_tvdb_id=0,
            total_episodes_owned=0,
        )
        runner = CliRunner()

        with (
            patch("complexionist.plex.PlexClient", return_value=plex),
            patch("complexionist.tvdb.TVDBClient", return_value=MagicMock()),
            patch("complexionist.gaps.EpisodeGapFinder", finder_cls),
        ):
            result = runner.invoke(main, ["tv", "--recent-threshold", "0"])

        assert result.exit_code == 0
        assert finder_cls.call_args.kwargs["recent_threshold_hours"] == 0

    def test_recent_threshold_defaults_from_config(self, config_env: Path) -> None:
        """Without the flag, recent_threshold_hours comes from config (default 24)."""
        plex, _ = _tv_scan_mocks()
        finder_cls = MagicMock()
        finder_cls.return_value.find_gaps.return_value = EpisodeGapReport(
            library_name="TV Shows",
            total_shows_scanned=0,
            shows_with_tvdb_id=0,
            total_episodes_owned=0,
        )
        runner = CliRunner()

        with (
            patch("complexionist.plex.PlexClient", return_value=plex),
            patch("complexionist.tvdb.TVDBClient", return_value=MagicMock()),
            patch("complexionist.gaps.EpisodeGapFinder", finder_cls),
        ):
            result = runner.invoke(main, ["tv"])

        assert result.exit_code == 0
        assert finder_cls.call_args.kwargs["recent_threshold_hours"] == 24


class TestScanCommand:
    """Tests for the combined scan command (movies + TV)."""

    @staticmethod
    def _mock_plex_dual() -> MagicMock:
        """Mock PlexClient exposing one movie and one TV library."""
        client = MagicMock()
        client.get_movies.return_value = []
        client.get_shows.return_value = []
        client.get_episodes.return_value = []
        movie_lib = MagicMock(title="Movies", type="movie", locations=["/movies"])
        tv_lib = MagicMock(title="TV Shows", type="show", locations=["/tv"])
        client.get_movie_libraries.return_value = [movie_lib]
        client.get_tv_libraries.return_value = [tv_lib]
        return client

    def _invoke_scan(self, args: list[str]) -> tuple[object, MagicMock, MagicMock]:
        """Run `scan` with mocked clients/finders; return (result, movie_cls, tv_cls)."""
        plex = self._mock_plex_dual()
        movie_finder_cls = MagicMock()
        movie_finder_cls.return_value.find_gaps.return_value = MovieGapReport(
            library_name="Movies",
            total_movies_scanned=0,
            movies_with_tmdb_id=0,
            movies_in_collections=0,
            unique_collections=0,
        )
        tv_finder_cls = MagicMock()
        tv_finder_cls.return_value.find_gaps.return_value = EpisodeGapReport(
            library_name="TV Shows",
            total_shows_scanned=0,
            shows_with_tvdb_id=0,
            total_episodes_owned=0,
        )
        runner = CliRunner()

        with (
            patch("complexionist.plex.PlexClient", return_value=plex),
            patch("complexionist.tmdb.TMDBClient", return_value=MagicMock()),
            patch("complexionist.tvdb.TVDBClient", return_value=MagicMock()),
            patch("complexionist.gaps.MovieGapFinder", movie_finder_cls),
            patch("complexionist.gaps.EpisodeGapFinder", tv_finder_cls),
        ):
            result = runner.invoke(main, ["scan", *args])

        return result, movie_finder_cls, tv_finder_cls

    def test_scan_include_specials_forwarded(self, config_env: Path) -> None:
        """--include-specials on scan reaches the TV gap finder."""
        result, _, tv_finder_cls = self._invoke_scan(["--include-specials"])

        assert result.exit_code == 0  # type: ignore[attr-defined]
        assert tv_finder_cls.call_args.kwargs["include_specials"] is True

    def test_scan_defaults_exclude_specials(self, config_env: Path) -> None:
        """Without the flag, scan excludes specials (include_specials=False)."""
        result, _, tv_finder_cls = self._invoke_scan([])

        assert result.exit_code == 0  # type: ignore[attr-defined]
        assert tv_finder_cls.call_args.kwargs["include_specials"] is False

    def test_scan_include_future_forwarded_to_both(self, config_env: Path) -> None:
        """--include-future on scan reaches both gap finders."""
        result, movie_finder_cls, tv_finder_cls = self._invoke_scan(["--include-future"])

        assert result.exit_code == 0  # type: ignore[attr-defined]
        assert movie_finder_cls.call_args.kwargs["include_future"] is True
        assert tv_finder_cls.call_args.kwargs["include_future"] is True


class TestCacheCommands:
    """Tests for cache subcommands."""

    def test_cache_stats_with_entries(self, config_env: Path) -> None:
        """cache stats reports entry counts by category."""
        from complexionist.cache import Cache

        seed = Cache(cache_dir=config_env)
        seed.set("tmdb", "movies", "100", {"id": 100}, ttl_hours=24)
        seed.set("tmdb", "movies", "101", {"id": 101}, ttl_hours=24)
        seed.set("tmdb", "collections", "1", {"id": 1}, ttl_hours=24)
        seed.flush()

        runner = CliRunner()
        result = runner.invoke(main, ["cache", "stats"])

        assert result.exit_code == 0
        assert "Total entries: 3" in result.output
        assert "TMDB movies" in result.output
        assert "TMDB collections" in result.output

    def test_cache_stats_empty(self, config_env: Path) -> None:
        """cache stats on an empty cache says so and exits 0."""
        runner = CliRunner()
        result = runner.invoke(main, ["cache", "stats"])

        assert result.exit_code == 0
        assert "Cache is empty" in result.output


class TestConfigShowCommand:
    """Tests for config show."""

    def test_config_show(self, config_env: Path) -> None:
        """config show prints servers (token masked) and options."""
        runner = CliRunner()
        result = runner.invoke(main, ["config", "show"])

        assert result.exit_code == 0
        assert "Current Configuration" in result.output
        assert "Test Server" in result.output
        # Token value must never be printed
        assert "test-token-12345" not in result.output
        assert "Token: (set)" in result.output
        assert "Recent threshold: 24 hours" in result.output
