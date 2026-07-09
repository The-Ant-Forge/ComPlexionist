"""Tests for core error logging (complexionist.errors)."""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

# Runs in a fresh interpreter so sys.modules reflects only what a CLI-style
# scan actually imports. Exercises both gap finders' error-logging paths.
_NO_FLET_SCRIPT = """
import sys
from unittest.mock import MagicMock

from complexionist.gaps.episodes import EpisodeGapFinder
from complexionist.gaps.movies import MovieGapFinder
from complexionist.tmdb import TMDBError
from complexionist.tvdb import TVDBError

# Exercise the movie finder's TMDB error-logging path
tmdb = MagicMock()
tmdb.is_movie_cached.return_value = True
tmdb.get_movie.side_effect = TMDBError("boom")
movie = MagicMock()
movie.tmdb_id = 1
movie.title = "Movie"
finder = MovieGapFinder(plex_client=MagicMock(), tmdb_client=tmdb)
finder._get_collection_ids([movie])

# Exercise the episode finder's TVDB error-logging path
tvdb = MagicMock()
tvdb.get_series.side_effect = TVDBError("boom")
show = MagicMock()
show.has_tvdb_id = True
show.tvdb_id = 1
show.title = "Show"
show.rating_key = 1
plex = MagicMock()
plex.get_shows.return_value = [show]
plex.get_tv_libraries.return_value = []
plex.get_episodes.return_value = []
efinder = EpisodeGapFinder(plex_client=plex, tvdb_client=tvdb)
efinder.find_gaps("TV")

assert "flet" not in sys.modules, "flet was imported during a CLI-style scan error path"
"""


def test_scan_error_paths_do_not_import_flet(tmp_path: Path) -> None:
    """Gap-finder error logging must not pull the Flet framework into CLI scans."""
    result = subprocess.run(
        [sys.executable, "-c", _NO_FLET_SCRIPT],
        cwd=tmp_path,  # log_error writes complexionist_errors.log to cwd
        capture_output=True,
        text=True,
        timeout=120,
    )
    assert result.returncode == 0, result.stderr


def test_log_error_includes_traceback(tmp_path: Path, monkeypatch) -> None:
    """log_error appends the full traceback when given a raised exception."""
    import complexionist.config as config_mod
    from complexionist.errors import log_error

    monkeypatch.setattr(config_mod, "get_exe_directory", lambda: tmp_path)

    def _boom() -> None:
        raise KeyError("tmdb_id")

    try:
        _boom()
    except KeyError as e:
        log_error(e, "Scan")

    content = (tmp_path / "complexionist_errors.log").read_text(encoding="utf-8")
    assert "Traceback (most recent call last)" in content
    assert "_boom" in content


def test_movie_finder_log_includes_context(tmp_path: Path, monkeypatch) -> None:
    """MovieGapFinder log entries name the library/server scan context."""
    from unittest.mock import MagicMock

    import complexionist.config as config_mod
    from complexionist.gaps.movies import MovieGapFinder
    from complexionist.tmdb import TMDBError

    monkeypatch.setattr(config_mod, "get_exe_directory", lambda: tmp_path)

    tmdb = MagicMock()
    tmdb.is_movie_cached.return_value = True
    tmdb.get_movie.side_effect = TMDBError("boom")
    movie = MagicMock()
    movie.tmdb_id = 1
    movie.title = "Movie"

    finder = MovieGapFinder(
        plex_client=MagicMock(),
        tmdb_client=tmdb,
        context="library 'Movies' on server 'Main Server'",
    )
    finder._get_collection_ids([movie])

    content = (tmp_path / "complexionist_errors.log").read_text(encoding="utf-8")
    assert "library 'Movies' on server 'Main Server'" in content


def test_episode_finder_log_includes_context(tmp_path: Path, monkeypatch) -> None:
    """EpisodeGapFinder log entries name the library/server scan context."""
    from unittest.mock import MagicMock

    import complexionist.config as config_mod
    from complexionist.gaps.episodes import EpisodeGapFinder
    from complexionist.tvdb import TVDBError

    monkeypatch.setattr(config_mod, "get_exe_directory", lambda: tmp_path)

    tvdb = MagicMock()
    tvdb.get_series.side_effect = TVDBError("boom")
    show = MagicMock()
    show.has_tvdb_id = True
    show.tvdb_id = 1
    show.title = "Show"
    show.rating_key = 1
    plex = MagicMock()
    plex.get_shows.return_value = [show]
    plex.get_tv_libraries.return_value = []
    plex.get_episodes.return_value = []

    finder = EpisodeGapFinder(
        plex_client=plex,
        tvdb_client=tvdb,
        context="library 'TV Shows' on server 'Main Server'",
    )
    finder.find_gaps("TV Shows")

    content = (tmp_path / "complexionist_errors.log").read_text(encoding="utf-8")
    assert "library 'TV Shows' on server 'Main Server'" in content


def test_log_error_writes_to_file(tmp_path: Path, monkeypatch) -> None:
    """log_error appends a timestamped entry to complexionist_errors.log."""
    import complexionist.config as config_mod
    from complexionist.errors import log_error

    monkeypatch.setattr(config_mod, "get_exe_directory", lambda: tmp_path)

    log_error(ValueError("something broke"), "unit test")

    log_file = tmp_path / "complexionist_errors.log"
    assert log_file.exists()
    content = log_file.read_text(encoding="utf-8")
    assert "ValueError" in content
    assert "unit test" in content
    assert "something broke" in content
