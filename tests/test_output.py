"""Tests for output formatting (JSON, CSV)."""

from __future__ import annotations

import json
from datetime import date

from complexionist.gaps.models import (
    CollectionGap,
    EpisodeGapReport,
    MissingEpisode,
    MissingMovie,
    MovieGapReport,
    SeasonGap,
    ShowGap,
)
from complexionist.output import MovieReportFormatter, TVReportFormatter


def _make_movie_report() -> MovieGapReport:
    """Create a sample movie gap report for testing."""
    return MovieGapReport(
        library_name="Movies",
        total_movies_scanned=100,
        movies_with_tmdb_id=95,
        movies_in_collections=50,
        unique_collections=10,
        total_missing=3,
        collections_with_gaps=[
            CollectionGap(
                collection_id=1241,
                collection_name="Harry Potter Collection",
                total_movies=8,
                owned_movies=5,
                missing_movies=[
                    MissingMovie(
                        tmdb_id=12444,
                        title="Harry Potter and the Goblet of Fire",
                        year=2005,
                        release_date=date(2005, 11, 18),
                    ),
                    MissingMovie(
                        tmdb_id=12445,
                        title="Harry Potter and the Order of the Phoenix",
                        year=2007,
                        release_date=date(2007, 7, 11),
                    ),
                ],
            ),
            CollectionGap(
                collection_id=9485,
                collection_name="Alien Collection",
                total_movies=4,
                owned_movies=3,
                missing_movies=[
                    MissingMovie(
                        tmdb_id=8077,
                        title="Alien Resurrection",
                        year=1997,
                        release_date=date(1997, 11, 26),
                    ),
                ],
            ),
        ],
    )


def _make_tv_report() -> EpisodeGapReport:
    """Create a sample TV gap report for testing."""
    return EpisodeGapReport(
        library_name="TV Shows",
        total_shows_scanned=30,
        shows_with_tvdb_id=28,
        total_episodes_owned=60,
        shows_with_gaps=[
            ShowGap(
                show_title="Breaking Bad",
                tvdb_id=81189,
                total_episodes=62,
                owned_episodes=60,
                seasons_with_gaps=[
                    SeasonGap(
                        season_number=5,
                        total_episodes=16,
                        owned_episodes=14,
                        missing_episodes=[
                            MissingEpisode(
                                tvdb_id=4849873,
                                season_number=5,
                                episode_number=15,
                                title="Granite State",
                                aired=date(2013, 9, 22),
                            ),
                            MissingEpisode(
                                tvdb_id=4849874,
                                season_number=5,
                                episode_number=16,
                                title="Felina",
                                aired=date(2013, 9, 29),
                            ),
                        ],
                    ),
                ],
            ),
        ],
    )


class TestMovieReportJSON:
    """Tests for MovieReportFormatter.to_json()."""

    def test_json_valid(self) -> None:
        report = _make_movie_report()
        formatter = MovieReportFormatter(report)
        result = json.loads(formatter.to_json())
        assert result["library_name"] == "Movies"
        assert result["total_movies_scanned"] == 100
        assert result["total_missing"] == 3

    def test_json_collections(self) -> None:
        report = _make_movie_report()
        formatter = MovieReportFormatter(report)
        result = json.loads(formatter.to_json())
        collections = result["collections"]
        assert len(collections) == 2
        assert collections[0]["name"] == "Harry Potter Collection"
        assert len(collections[0]["missing"]) == 2
        assert collections[1]["name"] == "Alien Collection"
        assert len(collections[1]["missing"]) == 1

    def test_json_movie_fields(self) -> None:
        report = _make_movie_report()
        formatter = MovieReportFormatter(report)
        result = json.loads(formatter.to_json())
        movie = result["collections"][0]["missing"][0]
        assert movie["tmdb_id"] == 12444
        assert movie["title"] == "Harry Potter and the Goblet of Fire"
        assert movie["year"] == 2005
        assert movie["release_date"] == "2005-11-18"

    def test_json_empty_report(self) -> None:
        report = MovieGapReport(
            library_name="Movies",
            total_movies_scanned=50,
            movies_with_tmdb_id=45,
            movies_in_collections=20,
            unique_collections=5,
            total_missing=0,
            collections_with_gaps=[],
        )
        formatter = MovieReportFormatter(report)
        result = json.loads(formatter.to_json())
        assert result["total_missing"] == 0
        assert result["collections"] == []


class TestMovieReportCSV:
    """Tests for MovieReportFormatter.to_csv()."""

    def test_csv_header(self) -> None:
        report = _make_movie_report()
        formatter = MovieReportFormatter(report)
        csv_text = formatter.to_csv()
        lines = csv_text.strip().splitlines()
        assert lines[0] == "Collection,Movie Title,Year,TMDB ID,Release Date,TMDB URL"

    def test_csv_row_count(self) -> None:
        report = _make_movie_report()
        formatter = MovieReportFormatter(report)
        csv_text = formatter.to_csv()
        lines = csv_text.strip().splitlines()
        assert len(lines) == 4  # header + 3 movies

    def test_csv_empty_report(self) -> None:
        report = MovieGapReport(
            library_name="Movies",
            total_movies_scanned=50,
            movies_with_tmdb_id=45,
            movies_in_collections=20,
            unique_collections=5,
            total_missing=0,
            collections_with_gaps=[],
        )
        formatter = MovieReportFormatter(report)
        csv_text = formatter.to_csv()
        lines = csv_text.strip().splitlines()
        assert len(lines) == 1  # header only


class TestTVReportJSON:
    """Tests for TVReportFormatter.to_json()."""

    def test_json_valid(self) -> None:
        report = _make_tv_report()
        formatter = TVReportFormatter(report)
        result = json.loads(formatter.to_json())
        assert result["library_name"] == "TV Shows"
        assert result["total_shows_scanned"] == 30
        assert result["total_missing"] == 2

    def test_json_shows(self) -> None:
        report = _make_tv_report()
        formatter = TVReportFormatter(report)
        result = json.loads(formatter.to_json())
        shows = result["shows"]
        assert len(shows) == 1
        assert shows[0]["title"] == "Breaking Bad"
        assert len(shows[0]["seasons"]) == 1
        assert len(shows[0]["seasons"][0]["missing"]) == 2

    def test_json_episode_fields(self) -> None:
        report = _make_tv_report()
        formatter = TVReportFormatter(report)
        result = json.loads(formatter.to_json())
        ep = result["shows"][0]["seasons"][0]["missing"][0]
        assert ep["episode_code"] == "S05E15"
        assert ep["title"] == "Granite State"
        assert ep["aired"] == "2013-09-22"


class TestTVReportCSV:
    """Tests for TVReportFormatter.to_csv()."""

    def test_csv_header(self) -> None:
        report = _make_tv_report()
        formatter = TVReportFormatter(report)
        csv_text = formatter.to_csv()
        lines = csv_text.strip().splitlines()
        assert "Show" in lines[0]
        assert "Season" in lines[0]

    def test_csv_row_count(self) -> None:
        report = _make_tv_report()
        formatter = TVReportFormatter(report)
        csv_text = formatter.to_csv()
        lines = csv_text.strip().splitlines()
        assert len(lines) == 3  # header + 2 episodes


class TestSanitizeFilename:
    """Tests for ReportFormatter._sanitize_filename()."""

    def test_normal_name(self) -> None:
        assert MovieReportFormatter._sanitize_filename("My Movies") == "My_Movies"

    def test_special_chars(self) -> None:
        result = MovieReportFormatter._sanitize_filename("Movies: 4K (HDR)")
        assert ":" not in result
        assert "(" not in result

    def test_empty(self) -> None:
        assert MovieReportFormatter._sanitize_filename("") == ""


class TestScoreColor:
    """Tests for ReportFormatter._get_score_color()."""

    def test_high_score(self) -> None:
        assert MovieReportFormatter._get_score_color(90.0) == "green"

    def test_medium_score(self) -> None:
        assert MovieReportFormatter._get_score_color(75.0) == "yellow"

    def test_low_score(self) -> None:
        assert MovieReportFormatter._get_score_color(30.0) == "red"
