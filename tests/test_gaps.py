"""Tests for the gap detection module."""

from datetime import date
from unittest.mock import MagicMock

from complexionist.gaps import (
    CollectionGap,
    EpisodeGapFinder,
    EpisodeGapReport,
    MissingEpisode,
    MissingMovie,
    MovieGapFinder,
    MovieGapReport,
    SeasonGap,
    ShowGap,
    parse_multi_episode_filename,
)
from complexionist.plex import PlexEpisode, PlexMovie, PlexShow
from complexionist.tmdb import TMDBCollection, TMDBMovie, TMDBMovieDetails
from complexionist.tvdb import TVDBEpisode


class TestGapModels:
    """Tests for gap detection data models."""

    def test_missing_movie_display_title_with_year(self) -> None:
        """Test display title includes year when available."""
        movie = MissingMovie(
            tmdb_id=123,
            title="Test Movie",
            year=2020,
        )
        assert movie.display_title == "Test Movie (2020)"

    def test_missing_movie_display_title_without_year(self) -> None:
        """Test display title without year."""
        movie = MissingMovie(
            tmdb_id=123,
            title="Test Movie",
        )
        assert movie.display_title == "Test Movie"

    def test_collection_gap_missing_count(self) -> None:
        """Test missing count calculation."""
        gap = CollectionGap(
            collection_id=1,
            collection_name="Test Collection",
            total_movies=5,
            owned_movies=3,
            missing_movies=[
                MissingMovie(tmdb_id=1, title="Movie 1"),
                MissingMovie(tmdb_id=2, title="Movie 2"),
            ],
        )
        assert gap.missing_count == 2

    def test_collection_gap_completion_percent(self) -> None:
        """Test completion percentage calculation."""
        gap = CollectionGap(
            collection_id=1,
            collection_name="Test Collection",
            total_movies=4,
            owned_movies=3,
            missing_movies=[MissingMovie(tmdb_id=1, title="Movie 1")],
        )
        assert gap.completion_percent == 75.0

    def test_collection_gap_completion_percent_empty(self) -> None:
        """Test completion percentage with zero total movies."""
        gap = CollectionGap(
            collection_id=1,
            collection_name="Empty Collection",
            total_movies=0,
            owned_movies=0,
            missing_movies=[],
        )
        assert gap.completion_percent == 100.0

    def test_movie_gap_report_total_missing(self) -> None:
        """Test total missing count across collections."""
        report = MovieGapReport(
            library_name="Movies",
            total_movies_scanned=100,
            movies_with_tmdb_id=95,
            movies_in_collections=50,
            unique_collections=10,
            collections_with_gaps=[
                CollectionGap(
                    collection_id=1,
                    collection_name="Collection 1",
                    total_movies=5,
                    owned_movies=3,
                    missing_movies=[
                        MissingMovie(tmdb_id=1, title="Movie 1"),
                        MissingMovie(tmdb_id=2, title="Movie 2"),
                    ],
                ),
                CollectionGap(
                    collection_id=2,
                    collection_name="Collection 2",
                    total_movies=3,
                    owned_movies=2,
                    missing_movies=[
                        MissingMovie(tmdb_id=3, title="Movie 3"),
                    ],
                ),
            ],
        )
        assert report.total_missing == 3

    def test_movie_gap_report_complete_collections(self) -> None:
        """Test count of complete collections."""
        report = MovieGapReport(
            library_name="Movies",
            total_movies_scanned=100,
            movies_with_tmdb_id=95,
            movies_in_collections=50,
            unique_collections=10,
            collections_with_gaps=[
                CollectionGap(
                    collection_id=1,
                    collection_name="Collection 1",
                    total_movies=5,
                    owned_movies=3,
                    missing_movies=[MissingMovie(tmdb_id=1, title="Movie 1")],
                ),
            ],
        )
        # 10 total - 1 with gaps = 9 complete
        assert report.complete_collections == 9


class TestMovieGapFinder:
    """Tests for the MovieGapFinder class."""

    def _create_mock_plex_client(
        self, movies: list[PlexMovie]
    ) -> MagicMock:
        """Create a mock Plex client."""
        mock_client = MagicMock()
        mock_client.get_movies.return_value = movies
        mock_client.get_movie_libraries.return_value = [
            MagicMock(title="Movies")
        ]
        return mock_client

    def _create_mock_tmdb_client(
        self,
        movie_collections: dict[int, int | None],
        collections: dict[int, TMDBCollection],
    ) -> MagicMock:
        """Create a mock TMDB client."""
        mock_client = MagicMock()

        def get_movie(movie_id: int) -> TMDBMovieDetails:
            collection_id = movie_collections.get(movie_id)
            collection_info = None
            if collection_id:
                collection_info = {
                    "id": collection_id,
                    "name": f"Collection {collection_id}",
                }
            return TMDBMovieDetails(
                id=movie_id,
                title=f"Movie {movie_id}",
                belongs_to_collection=collection_info,
            )

        def get_collection(collection_id: int) -> TMDBCollection:
            return collections[collection_id]

        mock_client.get_movie.side_effect = get_movie
        mock_client.get_collection.side_effect = get_collection

        return mock_client

    def test_find_gaps_empty_library(self) -> None:
        """Test with empty movie library."""
        plex = self._create_mock_plex_client([])
        tmdb = self._create_mock_tmdb_client({}, {})

        finder = MovieGapFinder(plex, tmdb)
        report = finder.find_gaps()

        assert report.total_movies_scanned == 0
        assert report.movies_with_tmdb_id == 0
        assert report.collections_with_gaps == []

    def test_find_gaps_no_collections(self) -> None:
        """Test when movies don't belong to any collections."""
        movies = [
            PlexMovie(rating_key="1", title="Movie 1", tmdb_id=100),
            PlexMovie(rating_key="2", title="Movie 2", tmdb_id=200),
        ]
        plex = self._create_mock_plex_client(movies)
        # Movies return no collections
        tmdb = self._create_mock_tmdb_client({100: None, 200: None}, {})

        finder = MovieGapFinder(plex, tmdb)
        report = finder.find_gaps()

        assert report.total_movies_scanned == 2
        assert report.movies_with_tmdb_id == 2
        assert report.movies_in_collections == 0
        assert report.collections_with_gaps == []

    def test_find_gaps_complete_collection(self) -> None:
        """Test when user owns all movies in a collection."""
        movies = [
            PlexMovie(rating_key="1", title="Movie 1", tmdb_id=100),
            PlexMovie(rating_key="2", title="Movie 2", tmdb_id=101),
        ]
        plex = self._create_mock_plex_client(movies)

        # Both movies belong to collection 1
        movie_collections = {100: 1, 101: 1}
        collections = {
            1: TMDBCollection(
                id=1,
                name="Complete Collection",
                parts=[
                    TMDBMovie(id=100, title="Movie 1", release_date=date(2020, 1, 1)),
                    TMDBMovie(id=101, title="Movie 2", release_date=date(2021, 1, 1)),
                ],
            ),
        }
        tmdb = self._create_mock_tmdb_client(movie_collections, collections)

        finder = MovieGapFinder(plex, tmdb)
        report = finder.find_gaps()

        assert report.unique_collections == 1
        assert report.collections_with_gaps == []

    def test_find_gaps_with_missing_movies(self) -> None:
        """Test when user is missing movies from a collection."""
        movies = [
            PlexMovie(rating_key="1", title="Alien", tmdb_id=348),
        ]
        plex = self._create_mock_plex_client(movies)

        movie_collections = {348: 8091}  # Alien Collection
        collections = {
            8091: TMDBCollection(
                id=8091,
                name="Alien Collection",
                parts=[
                    TMDBMovie(id=348, title="Alien", release_date=date(1979, 5, 25)),
                    TMDBMovie(id=679, title="Aliens", release_date=date(1986, 7, 18)),
                    TMDBMovie(id=8077, title="Alien 3", release_date=date(1992, 5, 22)),
                ],
            ),
        }
        tmdb = self._create_mock_tmdb_client(movie_collections, collections)

        finder = MovieGapFinder(plex, tmdb)
        report = finder.find_gaps()

        assert len(report.collections_with_gaps) == 1
        gap = report.collections_with_gaps[0]
        assert gap.collection_name == "Alien Collection"
        assert gap.owned_movies == 1
        assert gap.total_movies == 3
        assert gap.missing_count == 2
        assert {m.title for m in gap.missing_movies} == {"Aliens", "Alien 3"}

    def test_find_gaps_excludes_future_releases(self) -> None:
        """Test that future releases are excluded by default."""
        movies = [
            PlexMovie(rating_key="1", title="Released Movie", tmdb_id=100),
        ]
        plex = self._create_mock_plex_client(movies)

        movie_collections = {100: 1}
        collections = {
            1: TMDBCollection(
                id=1,
                name="Test Collection",
                parts=[
                    TMDBMovie(id=100, title="Released Movie", release_date=date(2020, 1, 1)),
                    TMDBMovie(id=101, title="Future Movie", release_date=date(2099, 12, 31)),
                ],
            ),
        }
        tmdb = self._create_mock_tmdb_client(movie_collections, collections)

        finder = MovieGapFinder(plex, tmdb, include_future=False)
        report = finder.find_gaps()

        # Collection should be complete (future movie excluded)
        assert report.collections_with_gaps == []

    def test_find_gaps_includes_future_when_enabled(self) -> None:
        """Test that future releases are included when flag is set."""
        movies = [
            PlexMovie(rating_key="1", title="Released Movie", tmdb_id=100),
        ]
        plex = self._create_mock_plex_client(movies)

        movie_collections = {100: 1}
        collections = {
            1: TMDBCollection(
                id=1,
                name="Test Collection",
                parts=[
                    TMDBMovie(id=100, title="Released Movie", release_date=date(2020, 1, 1)),
                    TMDBMovie(id=101, title="Future Movie", release_date=date(2099, 12, 31)),
                ],
            ),
        }
        tmdb = self._create_mock_tmdb_client(movie_collections, collections)

        finder = MovieGapFinder(plex, tmdb, include_future=True)
        report = finder.find_gaps()

        assert len(report.collections_with_gaps) == 1
        gap = report.collections_with_gaps[0]
        assert gap.missing_count == 1
        assert gap.missing_movies[0].title == "Future Movie"

    def test_find_gaps_progress_callback(self) -> None:
        """Test that progress callback is called."""
        movies = [
            PlexMovie(rating_key="1", title="Movie 1", tmdb_id=100),
        ]
        plex = self._create_mock_plex_client(movies)
        tmdb = self._create_mock_tmdb_client({100: None}, {})

        progress_calls = []

        def progress_callback(stage: str, current: int, total: int) -> None:
            progress_calls.append((stage, current, total))

        finder = MovieGapFinder(plex, tmdb, progress_callback=progress_callback)
        finder.find_gaps()

        # Should have progress updates
        assert len(progress_calls) > 0
        stages = {call[0] for call in progress_calls}
        assert "Fetching movies from Plex" in stages
        assert "Checking collection membership" in stages

    def test_find_gaps_movies_without_tmdb_id_skipped(self) -> None:
        """Test that movies without TMDB IDs are counted but skipped."""
        movies = [
            PlexMovie(rating_key="1", title="With ID", tmdb_id=100),
            PlexMovie(rating_key="2", title="Without ID"),  # No TMDB ID
        ]
        plex = self._create_mock_plex_client(movies)
        tmdb = self._create_mock_tmdb_client({100: None}, {})

        finder = MovieGapFinder(plex, tmdb)
        report = finder.find_gaps()

        assert report.total_movies_scanned == 2
        assert report.movies_with_tmdb_id == 1


# ============================================================================
# Episode Gap Detection Tests
# ============================================================================


class TestEpisodeGapModels:
    """Tests for episode gap detection data models."""

    def test_missing_episode_episode_code(self) -> None:
        """Test episode code formatting."""
        ep = MissingEpisode(
            tvdb_id=123,
            season_number=2,
            episode_number=5,
            title="Test Episode",
        )
        assert ep.episode_code == "S02E05"

    def test_missing_episode_display_title_with_title(self) -> None:
        """Test display title includes episode title when available."""
        ep = MissingEpisode(
            tvdb_id=123,
            season_number=1,
            episode_number=3,
            title="Pilot",
        )
        assert ep.display_title == "S01E03 - Pilot"

    def test_missing_episode_display_title_without_title(self) -> None:
        """Test display title without episode title."""
        ep = MissingEpisode(
            tvdb_id=123,
            season_number=1,
            episode_number=3,
        )
        assert ep.display_title == "S01E03"

    def test_season_gap_missing_count(self) -> None:
        """Test missing count calculation."""
        gap = SeasonGap(
            season_number=1,
            total_episodes=10,
            owned_episodes=7,
            missing_episodes=[
                MissingEpisode(tvdb_id=1, season_number=1, episode_number=3),
                MissingEpisode(tvdb_id=2, season_number=1, episode_number=5),
                MissingEpisode(tvdb_id=3, season_number=1, episode_number=8),
            ],
        )
        assert gap.missing_count == 3

    def test_show_gap_missing_count(self) -> None:
        """Test total missing count across seasons."""
        show = ShowGap(
            tvdb_id=100,
            show_title="Test Show",
            total_episodes=20,
            owned_episodes=15,
            seasons_with_gaps=[
                SeasonGap(
                    season_number=1,
                    total_episodes=10,
                    owned_episodes=8,
                    missing_episodes=[
                        MissingEpisode(tvdb_id=1, season_number=1, episode_number=3),
                        MissingEpisode(tvdb_id=2, season_number=1, episode_number=5),
                    ],
                ),
                SeasonGap(
                    season_number=2,
                    total_episodes=10,
                    owned_episodes=7,
                    missing_episodes=[
                        MissingEpisode(tvdb_id=3, season_number=2, episode_number=1),
                        MissingEpisode(tvdb_id=4, season_number=2, episode_number=2),
                        MissingEpisode(tvdb_id=5, season_number=2, episode_number=3),
                    ],
                ),
            ],
        )
        assert show.missing_count == 5

    def test_show_gap_completion_percent(self) -> None:
        """Test completion percentage calculation."""
        show = ShowGap(
            tvdb_id=100,
            show_title="Test Show",
            total_episodes=20,
            owned_episodes=15,
            seasons_with_gaps=[],
        )
        assert show.completion_percent == 75.0

    def test_show_gap_completion_percent_empty(self) -> None:
        """Test completion percentage with zero total episodes."""
        show = ShowGap(
            tvdb_id=100,
            show_title="Empty Show",
            total_episodes=0,
            owned_episodes=0,
            seasons_with_gaps=[],
        )
        assert show.completion_percent == 100.0

    def test_episode_gap_report_total_missing(self) -> None:
        """Test total missing count across shows."""
        report = EpisodeGapReport(
            library_name="TV Shows",
            total_shows_scanned=10,
            shows_with_tvdb_id=8,
            total_episodes_owned=100,
            shows_with_gaps=[
                ShowGap(
                    tvdb_id=1,
                    show_title="Show 1",
                    total_episodes=20,
                    owned_episodes=18,
                    seasons_with_gaps=[
                        SeasonGap(
                            season_number=1,
                            total_episodes=10,
                            owned_episodes=9,
                            missing_episodes=[
                                MissingEpisode(tvdb_id=1, season_number=1, episode_number=5),
                            ],
                        ),
                        SeasonGap(
                            season_number=2,
                            total_episodes=10,
                            owned_episodes=9,
                            missing_episodes=[
                                MissingEpisode(tvdb_id=2, season_number=2, episode_number=3),
                            ],
                        ),
                    ],
                ),
                ShowGap(
                    tvdb_id=2,
                    show_title="Show 2",
                    total_episodes=15,
                    owned_episodes=12,
                    seasons_with_gaps=[
                        SeasonGap(
                            season_number=1,
                            total_episodes=15,
                            owned_episodes=12,
                            missing_episodes=[
                                MissingEpisode(tvdb_id=3, season_number=1, episode_number=1),
                                MissingEpisode(tvdb_id=4, season_number=1, episode_number=2),
                                MissingEpisode(tvdb_id=5, season_number=1, episode_number=3),
                            ],
                        ),
                    ],
                ),
            ],
        )
        assert report.total_missing == 5

    def test_episode_gap_report_complete_shows(self) -> None:
        """Test count of complete shows."""
        report = EpisodeGapReport(
            library_name="TV Shows",
            total_shows_scanned=10,
            shows_with_tvdb_id=8,
            total_episodes_owned=100,
            shows_with_gaps=[
                ShowGap(
                    tvdb_id=1,
                    show_title="Show 1",
                    total_episodes=10,
                    owned_episodes=8,
                    seasons_with_gaps=[],
                ),
            ],
        )
        # 8 with TVDB ID - 1 with gaps = 7 complete
        assert report.complete_shows == 7


class TestMultiEpisodeParsing:
    """Tests for multi-episode filename parsing."""

    def test_parse_multi_episode_dash_numbers(self) -> None:
        """Test parsing S02E01-02 format."""
        result = parse_multi_episode_filename("Show.S02E01-02.720p.mkv")
        assert (2, 1) in result
        assert (2, 2) in result

    def test_parse_multi_episode_dash_e_prefix(self) -> None:
        """Test parsing S02E01-E02 format."""
        result = parse_multi_episode_filename("Show.S02E01-E02.720p.mkv")
        assert (2, 1) in result
        assert (2, 2) in result

    def test_parse_multi_episode_consecutive_e(self) -> None:
        """Test parsing S02E01E02 format."""
        result = parse_multi_episode_filename("Show.S02E01E02.720p.mkv")
        assert (2, 1) in result
        assert (2, 2) in result

    def test_parse_multi_episode_none_path(self) -> None:
        """Test parsing None file path."""
        result = parse_multi_episode_filename(None)
        assert result == []

    def test_parse_multi_episode_no_match(self) -> None:
        """Test parsing single episode file."""
        result = parse_multi_episode_filename("Show.S02E01.720p.mkv")
        assert result == []

    def test_parse_multi_episode_case_insensitive(self) -> None:
        """Test case-insensitive parsing."""
        result = parse_multi_episode_filename("show.s02e01-02.720p.mkv")
        assert (2, 1) in result
        assert (2, 2) in result


class TestEpisodeGapFinder:
    """Tests for the EpisodeGapFinder class."""

    def _create_mock_plex_client(
        self,
        shows: list[PlexShow],
        episodes_by_show: dict[str, list[PlexEpisode]],
    ) -> MagicMock:
        """Create a mock Plex client."""
        mock_client = MagicMock()
        mock_client.get_shows.return_value = shows
        mock_client.get_tv_libraries.return_value = [MagicMock(title="TV Shows")]

        def get_episodes(rating_key: str) -> list[PlexEpisode]:
            return episodes_by_show.get(rating_key, [])

        mock_client.get_episodes.side_effect = get_episodes
        return mock_client

    def _create_mock_tvdb_client(
        self,
        episodes_by_series: dict[int, list[TVDBEpisode]],
    ) -> MagicMock:
        """Create a mock TVDB client."""
        mock_client = MagicMock()

        def get_series_episodes(series_id: int) -> list[TVDBEpisode]:
            return episodes_by_series.get(series_id, [])

        mock_client.get_series_episodes.side_effect = get_series_episodes
        mock_client.test_connection.return_value = True
        return mock_client

    def test_find_gaps_empty_library(self) -> None:
        """Test with empty TV library."""
        plex = self._create_mock_plex_client([], {})
        tvdb = self._create_mock_tvdb_client({})

        finder = EpisodeGapFinder(plex, tvdb)
        report = finder.find_gaps()

        assert report.total_shows_scanned == 0
        assert report.shows_with_tvdb_id == 0
        assert report.shows_with_gaps == []

    def test_find_gaps_complete_show(self) -> None:
        """Test when user owns all episodes of a show."""
        shows = [PlexShow(rating_key="1", title="Complete Show", tvdb_id=100)]
        plex_episodes = {
            "1": [
                PlexEpisode(rating_key="e1", title="Ep 1", season_number=1, episode_number=1),
                PlexEpisode(rating_key="e2", title="Ep 2", season_number=1, episode_number=2),
            ]
        }
        plex = self._create_mock_plex_client(shows, plex_episodes)

        tvdb_episodes = {
            100: [
                TVDBEpisode(id=1, seriesId=100, seasonNumber=1, number=1, aired=date(2020, 1, 1)),
                TVDBEpisode(id=2, seriesId=100, seasonNumber=1, number=2, aired=date(2020, 1, 8)),
            ]
        }
        tvdb = self._create_mock_tvdb_client(tvdb_episodes)

        finder = EpisodeGapFinder(plex, tvdb)
        report = finder.find_gaps()

        assert report.total_shows_scanned == 1
        assert report.shows_with_tvdb_id == 1
        assert report.shows_with_gaps == []

    def test_find_gaps_with_missing_episodes(self) -> None:
        """Test when user is missing episodes."""
        shows = [PlexShow(rating_key="1", title="Incomplete Show", tvdb_id=100)]
        plex_episodes = {
            "1": [
                PlexEpisode(rating_key="e1", title="Ep 1", season_number=1, episode_number=1),
                # Missing episode 2
            ]
        }
        plex = self._create_mock_plex_client(shows, plex_episodes)

        tvdb_episodes = {
            100: [
                TVDBEpisode(id=1, seriesId=100, seasonNumber=1, number=1, name="Pilot", aired=date(2020, 1, 1)),
                TVDBEpisode(id=2, seriesId=100, seasonNumber=1, number=2, name="Second", aired=date(2020, 1, 8)),
            ]
        }
        tvdb = self._create_mock_tvdb_client(tvdb_episodes)

        finder = EpisodeGapFinder(plex, tvdb)
        report = finder.find_gaps()

        assert len(report.shows_with_gaps) == 1
        show = report.shows_with_gaps[0]
        assert show.show_title == "Incomplete Show"
        assert show.missing_count == 1
        assert len(show.seasons_with_gaps) == 1
        assert show.seasons_with_gaps[0].missing_episodes[0].title == "Second"

    def test_find_gaps_excludes_specials_by_default(self) -> None:
        """Test that Season 0 (specials) are excluded by default."""
        shows = [PlexShow(rating_key="1", title="Show", tvdb_id=100)]
        plex_episodes = {
            "1": [
                PlexEpisode(rating_key="e1", title="Ep 1", season_number=1, episode_number=1),
            ]
        }
        plex = self._create_mock_plex_client(shows, plex_episodes)

        tvdb_episodes = {
            100: [
                TVDBEpisode(id=1, seriesId=100, seasonNumber=1, number=1, aired=date(2020, 1, 1)),
                TVDBEpisode(id=2, seriesId=100, seasonNumber=0, number=1, aired=date(2020, 1, 1)),  # Special
            ]
        }
        tvdb = self._create_mock_tvdb_client(tvdb_episodes)

        finder = EpisodeGapFinder(plex, tvdb, include_specials=False)
        report = finder.find_gaps()

        # Should be complete (special excluded)
        assert report.shows_with_gaps == []

    def test_find_gaps_includes_specials_when_enabled(self) -> None:
        """Test that specials are included when flag is set."""
        shows = [PlexShow(rating_key="1", title="Show", tvdb_id=100)]
        plex_episodes = {
            "1": [
                PlexEpisode(rating_key="e1", title="Ep 1", season_number=1, episode_number=1),
            ]
        }
        plex = self._create_mock_plex_client(shows, plex_episodes)

        tvdb_episodes = {
            100: [
                TVDBEpisode(id=1, seriesId=100, seasonNumber=1, number=1, aired=date(2020, 1, 1)),
                TVDBEpisode(id=2, seriesId=100, seasonNumber=0, number=1, name="Special", aired=date(2020, 1, 1)),
            ]
        }
        tvdb = self._create_mock_tvdb_client(tvdb_episodes)

        finder = EpisodeGapFinder(plex, tvdb, include_specials=True)
        report = finder.find_gaps()

        assert len(report.shows_with_gaps) == 1
        assert report.shows_with_gaps[0].missing_count == 1

    def test_find_gaps_excludes_future_by_default(self) -> None:
        """Test that unaired episodes are excluded by default."""
        shows = [PlexShow(rating_key="1", title="Show", tvdb_id=100)]
        plex_episodes = {
            "1": [
                PlexEpisode(rating_key="e1", title="Ep 1", season_number=1, episode_number=1),
            ]
        }
        plex = self._create_mock_plex_client(shows, plex_episodes)

        tvdb_episodes = {
            100: [
                TVDBEpisode(id=1, seriesId=100, seasonNumber=1, number=1, aired=date(2020, 1, 1)),
                TVDBEpisode(id=2, seriesId=100, seasonNumber=1, number=2, aired=date(2099, 12, 31)),  # Future
            ]
        }
        tvdb = self._create_mock_tvdb_client(tvdb_episodes)

        finder = EpisodeGapFinder(plex, tvdb, include_future=False)
        report = finder.find_gaps()

        # Should be complete (future excluded)
        assert report.shows_with_gaps == []

    def test_find_gaps_includes_future_when_enabled(self) -> None:
        """Test that future episodes are included when flag is set."""
        shows = [PlexShow(rating_key="1", title="Show", tvdb_id=100)]
        plex_episodes = {
            "1": [
                PlexEpisode(rating_key="e1", title="Ep 1", season_number=1, episode_number=1),
            ]
        }
        plex = self._create_mock_plex_client(shows, plex_episodes)

        tvdb_episodes = {
            100: [
                TVDBEpisode(id=1, seriesId=100, seasonNumber=1, number=1, aired=date(2020, 1, 1)),
                TVDBEpisode(id=2, seriesId=100, seasonNumber=1, number=2, name="Future Ep", aired=date(2099, 12, 31)),
            ]
        }
        tvdb = self._create_mock_tvdb_client(tvdb_episodes)

        finder = EpisodeGapFinder(plex, tvdb, include_future=True)
        report = finder.find_gaps()

        assert len(report.shows_with_gaps) == 1
        assert report.shows_with_gaps[0].missing_count == 1

    def test_find_gaps_multi_episode_files(self) -> None:
        """Test that multi-episode files mark multiple episodes as owned."""
        shows = [PlexShow(rating_key="1", title="Show", tvdb_id=100)]
        plex_episodes = {
            "1": [
                PlexEpisode(
                    rating_key="e1",
                    title="Pilot",
                    season_number=1,
                    episode_number=1,
                    file_path="/media/Show.S01E01-02.mkv",  # Multi-episode file
                ),
            ]
        }
        plex = self._create_mock_plex_client(shows, plex_episodes)

        tvdb_episodes = {
            100: [
                TVDBEpisode(id=1, seriesId=100, seasonNumber=1, number=1, aired=date(2020, 1, 1)),
                TVDBEpisode(id=2, seriesId=100, seasonNumber=1, number=2, aired=date(2020, 1, 8)),
            ]
        }
        tvdb = self._create_mock_tvdb_client(tvdb_episodes)

        finder = EpisodeGapFinder(plex, tvdb)
        report = finder.find_gaps()

        # Both episodes should be marked as owned
        assert report.shows_with_gaps == []

    def test_find_gaps_shows_without_tvdb_id_skipped(self) -> None:
        """Test that shows without TVDB IDs are counted but skipped."""
        shows = [
            PlexShow(rating_key="1", title="With ID", tvdb_id=100),
            PlexShow(rating_key="2", title="Without ID"),  # No TVDB ID
        ]
        plex_episodes = {
            "1": [
                PlexEpisode(rating_key="e1", title="Ep 1", season_number=1, episode_number=1),
            ]
        }
        plex = self._create_mock_plex_client(shows, plex_episodes)

        tvdb_episodes = {
            100: [
                TVDBEpisode(id=1, seriesId=100, seasonNumber=1, number=1, aired=date(2020, 1, 1)),
            ]
        }
        tvdb = self._create_mock_tvdb_client(tvdb_episodes)

        finder = EpisodeGapFinder(plex, tvdb)
        report = finder.find_gaps()

        assert report.total_shows_scanned == 2
        assert report.shows_with_tvdb_id == 1
