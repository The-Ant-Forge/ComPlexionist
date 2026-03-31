"""Tests for the gap detection module."""

from datetime import date, timedelta
from unittest.mock import MagicMock

from complexionist.gaps import (
    CollectionGap,
    EpisodeGapFinder,
    EpisodeGapReport,
    MissingEpisode,
    MissingMovie,
    MovieGapFinder,
    MovieGapReport,
    OwnedMovie,
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

    def test_complete_collections_with_disorganized(self) -> None:
        """Test complete_collections count includes disorganized as complete."""
        report = MovieGapReport(
            library_name="Movies",
            total_movies_scanned=100,
            movies_with_tmdb_id=95,
            movies_in_collections=50,
            unique_collections=10,
            collections_with_gaps=[
                CollectionGap(
                    collection_id=1,
                    collection_name="Incomplete",
                    total_movies=5,
                    owned_movies=3,
                    missing_movies=[MissingMovie(tmdb_id=1, title="Movie 1")],
                ),
                CollectionGap(
                    collection_id=2,
                    collection_name="Disorganized",
                    total_movies=3,
                    owned_movies=3,
                    missing_movies=[],
                    is_complete=True,
                ),
            ],
        )
        # 10 total - 1 incomplete = 9 complete (disorganized counts as complete)
        assert report.complete_collections == 9

    def test_movies_in_different_folders_same_grandparent(self) -> None:
        """Test movies in same grandparent directory are organized."""
        gap = CollectionGap(
            collection_id=1,
            collection_name="Die Hard Collection",
            total_movies=2,
            owned_movies=2,
            owned_movie_list=[
                OwnedMovie(
                    tmdb_id=1,
                    title="Die Hard",
                    file_path="/volume1/Movies/Die Hard (1988)/Die Hard (1988).mkv",
                ),
                OwnedMovie(
                    tmdb_id=2,
                    title="Die Hard 2",
                    file_path="/volume1/Movies/Die Hard 2 (1990)/Die Hard 2 (1990).mkv",
                ),
            ],
            library_locations=["/volume1/Movies"],
        )
        # Same grandparent (/volume1/Movies) but it IS the library root -> disorganized
        assert gap.movies_in_different_folders is True

    def test_movies_in_different_folders_organized(self) -> None:
        """Test movies in collection subfolder are organized."""
        gap = CollectionGap(
            collection_id=1,
            collection_name="Die Hard Collection",
            total_movies=2,
            owned_movies=2,
            owned_movie_list=[
                OwnedMovie(
                    tmdb_id=1,
                    title="Die Hard",
                    file_path="/volume1/Movies/Die Hard/Die Hard (1988)/Die Hard (1988).mkv",
                ),
                OwnedMovie(
                    tmdb_id=2,
                    title="Die Hard 2",
                    file_path="/volume1/Movies/Die Hard/Die Hard 2 (1990)/Die Hard 2 (1990).mkv",
                ),
            ],
            library_locations=["/volume1/Movies"],
        )
        # Same grandparent (/volume1/Movies/Die Hard) which is NOT library root -> organized
        assert gap.movies_in_different_folders is False

    def test_movies_in_different_folders_scattered(self) -> None:
        """Test movies in different grandparent directories are disorganized."""
        gap = CollectionGap(
            collection_id=1,
            collection_name="Die Hard Collection",
            total_movies=2,
            owned_movies=2,
            owned_movie_list=[
                OwnedMovie(
                    tmdb_id=1,
                    title="Die Hard",
                    file_path="/volume1/Movies/Die Hard/Die Hard (1988)/Die Hard (1988).mkv",
                ),
                OwnedMovie(
                    tmdb_id=2,
                    title="Die Hard 2",
                    file_path="/volume1/Movies/Die Hard 2 (1990)/Die Hard 2 (1990).mkv",
                ),
            ],
            library_locations=["/volume1/Movies"],
        )
        # Different grandparents -> disorganized
        assert gap.movies_in_different_folders is True

    def test_movies_in_different_folders_same_parent(self) -> None:
        """Test movies directly in same folder (no movie subfolders) are organized."""
        gap = CollectionGap(
            collection_id=1,
            collection_name="Garage Sale Mysteries Collection",
            total_movies=6,
            owned_movies=6,
            owned_movie_list=[
                OwnedMovie(
                    tmdb_id=1,
                    title="Garage Sale Mysteries",
                    file_path="/volume1/Movies/Garage Sale Mysteries/Garage Sale Mysteries (2013).mkv",
                ),
                OwnedMovie(
                    tmdb_id=2,
                    title="Garage Sale Mysteries 2",
                    file_path="/volume1/Movies/Garage Sale Mysteries/Garage Sale Mysteries 2 (2015).mkv",
                ),
            ],
            library_locations=["/volume1/Movies"],
        )
        # Same parent (/volume1/Movies/Garage Sale Mysteries) not library root -> organized
        assert gap.movies_in_different_folders is False

    def test_movies_in_different_folders_same_parent_library_root(self) -> None:
        """Test movies directly in library root (no subfolders at all) are disorganized."""
        gap = CollectionGap(
            collection_id=1,
            collection_name="Test Collection",
            total_movies=2,
            owned_movies=2,
            owned_movie_list=[
                OwnedMovie(
                    tmdb_id=1,
                    title="Movie 1",
                    file_path="/volume1/Movies/Movie 1 (2020).mkv",
                ),
                OwnedMovie(
                    tmdb_id=2,
                    title="Movie 2",
                    file_path="/volume1/Movies/Movie 2 (2021).mkv",
                ),
            ],
            library_locations=["/volume1/Movies"],
        )
        # Same parent but it IS the library root -> disorganized
        assert gap.movies_in_different_folders is True

    def test_movies_in_different_folders_single_movie(self) -> None:
        """Test single movie cannot be disorganized."""
        gap = CollectionGap(
            collection_id=1,
            collection_name="Test",
            total_movies=1,
            owned_movies=1,
            owned_movie_list=[
                OwnedMovie(
                    tmdb_id=1,
                    title="Movie 1",
                    file_path="/volume1/Movies/Movie 1 (2020)/Movie 1 (2020).mkv",
                ),
            ],
            library_locations=["/volume1/Movies"],
        )
        assert gap.movies_in_different_folders is False


class TestMovieGapFinder:
    """Tests for the MovieGapFinder class."""

    def _create_mock_plex_client(self, movies: list[PlexMovie]) -> MagicMock:
        """Create a mock Plex client."""
        mock_client = MagicMock()
        mock_client.get_movies.return_value = movies
        mock_client.get_movie_libraries.return_value = [MagicMock(title="Movies")]
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

        finder = MovieGapFinder(plex, tmdb, min_owned=1)
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

        finder = MovieGapFinder(plex, tmdb, include_future=True, min_owned=1)
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

        # Should have progress updates for stages that MovieGapFinder controls
        # Note: "Fetching movies from Plex" comes from plex client, not mocked
        assert len(progress_calls) > 0
        stages = {call[0] for call in progress_calls}
        assert "Checking: Movie 1" in stages

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

    def test_find_gaps_min_collection_size(self) -> None:
        """Test that small collections are excluded."""
        movies = [
            PlexMovie(rating_key="1", title="Movie 1", tmdb_id=100),
        ]
        plex = self._create_mock_plex_client(movies)

        # Collection with only 2 movies (1 owned, 1 missing)
        movie_collections = {100: 1}
        collections = {
            1: TMDBCollection(
                id=1,
                name="Small Collection",
                parts=[
                    TMDBMovie(id=100, title="Movie 1", release_date=date(2020, 1, 1)),
                    TMDBMovie(id=101, title="Movie 2", release_date=date(2021, 1, 1)),
                ],
            ),
        }
        tmdb = self._create_mock_tmdb_client(movie_collections, collections)

        # With min_collection_size=3, this collection should be skipped
        finder = MovieGapFinder(plex, tmdb, min_collection_size=3)
        report = finder.find_gaps()

        assert report.collections_with_gaps == []

    def test_find_gaps_min_collection_size_includes_large(self) -> None:
        """Test that large collections are included."""
        movies = [
            PlexMovie(rating_key="1", title="Movie 1", tmdb_id=100),
        ]
        plex = self._create_mock_plex_client(movies)

        # Collection with 3 movies
        movie_collections = {100: 1}
        collections = {
            1: TMDBCollection(
                id=1,
                name="Large Collection",
                parts=[
                    TMDBMovie(id=100, title="Movie 1", release_date=date(2020, 1, 1)),
                    TMDBMovie(id=101, title="Movie 2", release_date=date(2021, 1, 1)),
                    TMDBMovie(id=102, title="Movie 3", release_date=date(2022, 1, 1)),
                ],
            ),
        }
        tmdb = self._create_mock_tmdb_client(movie_collections, collections)

        # With min_collection_size=3, this collection should be included
        finder = MovieGapFinder(plex, tmdb, min_collection_size=3, min_owned=1)
        report = finder.find_gaps()

        assert len(report.collections_with_gaps) == 1
        assert report.collections_with_gaps[0].missing_count == 2

    def test_find_gaps_excluded_collections(self) -> None:
        """Test that excluded collections are skipped."""
        movies = [
            PlexMovie(rating_key="1", title="Movie 1", tmdb_id=100),
        ]
        plex = self._create_mock_plex_client(movies)

        movie_collections = {100: 1}
        collections = {
            1: TMDBCollection(
                id=1,
                name="Skip This Collection",
                parts=[
                    TMDBMovie(id=100, title="Movie 1", release_date=date(2020, 1, 1)),
                    TMDBMovie(id=101, title="Movie 2", release_date=date(2021, 1, 1)),
                ],
            ),
        }
        tmdb = self._create_mock_tmdb_client(movie_collections, collections)

        finder = MovieGapFinder(
            plex,
            tmdb,
            excluded_collections=["Skip This Collection"],
        )
        report = finder.find_gaps()

        assert report.collections_with_gaps == []

    def test_find_gaps_excluded_collections_case_insensitive(self) -> None:
        """Test that collection exclusions are case-insensitive."""
        movies = [
            PlexMovie(rating_key="1", title="Movie 1", tmdb_id=100),
        ]
        plex = self._create_mock_plex_client(movies)

        movie_collections = {100: 1}
        collections = {
            1: TMDBCollection(
                id=1,
                name="The Collection",
                parts=[
                    TMDBMovie(id=100, title="Movie 1", release_date=date(2020, 1, 1)),
                    TMDBMovie(id=101, title="Movie 2", release_date=date(2021, 1, 1)),
                ],
            ),
        }
        tmdb = self._create_mock_tmdb_client(movie_collections, collections)

        finder = MovieGapFinder(
            plex,
            tmdb,
            excluded_collections=["THE COLLECTION"],  # Different case
        )
        report = finder.find_gaps()

        assert report.collections_with_gaps == []

    def test_find_gaps_min_owned_filters_collections(self) -> None:
        """Test that collections are filtered by min_owned threshold."""
        # User owns only 1 movie from a collection
        movies = [
            PlexMovie(rating_key="1", title="Movie 1", tmdb_id=100),
        ]
        plex = self._create_mock_plex_client(movies)

        movie_collections = {100: 1}
        collections = {
            1: TMDBCollection(
                id=1,
                name="Test Collection",
                parts=[
                    TMDBMovie(id=100, title="Movie 1", release_date=date(2020, 1, 1)),
                    TMDBMovie(id=101, title="Movie 2", release_date=date(2021, 1, 1)),
                    TMDBMovie(id=102, title="Movie 3", release_date=date(2022, 1, 1)),
                ],
            ),
        }
        tmdb = self._create_mock_tmdb_client(movie_collections, collections)

        # With min_owned=2, collection should be filtered out (only owns 1)
        finder = MovieGapFinder(plex, tmdb, min_owned=2)
        report = finder.find_gaps()
        assert report.collections_with_gaps == []

        # With min_owned=1, collection should be included
        finder = MovieGapFinder(plex, tmdb, min_owned=1)
        report = finder.find_gaps()
        assert len(report.collections_with_gaps) == 1
        assert report.collections_with_gaps[0].missing_count == 2

    def test_find_gaps_min_owned_includes_when_threshold_met(self) -> None:
        """Test that collections are included when min_owned threshold is met."""
        # User owns 2 movies from a collection
        movies = [
            PlexMovie(rating_key="1", title="Movie 1", tmdb_id=100),
            PlexMovie(rating_key="2", title="Movie 2", tmdb_id=101),
        ]
        plex = self._create_mock_plex_client(movies)

        movie_collections = {100: 1, 101: 1}
        collections = {
            1: TMDBCollection(
                id=1,
                name="Test Collection",
                parts=[
                    TMDBMovie(id=100, title="Movie 1", release_date=date(2020, 1, 1)),
                    TMDBMovie(id=101, title="Movie 2", release_date=date(2021, 1, 1)),
                    TMDBMovie(id=102, title="Movie 3", release_date=date(2022, 1, 1)),
                ],
            ),
        }
        tmdb = self._create_mock_tmdb_client(movie_collections, collections)

        # With min_owned=2, collection should be included (owns 2)
        finder = MovieGapFinder(plex, tmdb, min_owned=2)
        report = finder.find_gaps()
        assert len(report.collections_with_gaps) == 1
        gap = report.collections_with_gaps[0]
        assert gap.owned_movies == 2
        assert gap.missing_count == 1

    def test_get_collection_ids_parallel_produces_same_results(self) -> None:
        """Parallel lookup should produce identical results to sequential."""
        movies = [
            PlexMovie(rating_key=str(i), title=f"Movie {i}", tmdb_id=100 + i)
            for i in range(10)
        ]
        plex = self._create_mock_plex_client(movies)

        # Movies 100-104 in collection 1, 105-109 in collection 2
        movie_collections = {100 + i: 1 if i < 5 else 2 for i in range(10)}
        past = date(2020, 1, 1)
        collections = {
            1: TMDBCollection(
                id=1,
                name="Collection A",
                parts=[
                    TMDBMovie(id=100 + i, title=f"Movie {i}", release_date=past)
                    for i in range(5)  # 5 owned
                ]
                + [
                    TMDBMovie(id=200 + i, title=f"Missing A{i}", release_date=past)
                    for i in range(2)  # 2 missing (IDs 200, 201 not owned)
                ],
            ),
            2: TMDBCollection(
                id=2,
                name="Collection B",
                parts=[
                    TMDBMovie(id=105 + i, title=f"Movie {5 + i}", release_date=past)
                    for i in range(5)  # 5 owned
                ]
                + [
                    TMDBMovie(id=210 + i, title=f"Missing B{i}", release_date=past)
                    for i in range(3)  # 3 missing (IDs 210-212 not owned)
                ],
            ),
        }
        tmdb = self._create_mock_tmdb_client(movie_collections, collections)

        finder = MovieGapFinder(plex, tmdb)
        report = finder.find_gaps()

        assert report.movies_in_collections == 10
        assert report.unique_collections == 2
        assert len(report.collections_with_gaps) == 2

    def test_get_collection_ids_handles_errors_in_parallel(self) -> None:
        """Errors for individual movies should not crash the parallel lookup."""
        movies = [
            PlexMovie(rating_key="1", title="Good Movie", tmdb_id=100),
            PlexMovie(rating_key="2", title="Bad Movie", tmdb_id=200),
            PlexMovie(rating_key="3", title="Also Good", tmdb_id=300),
        ]
        plex = self._create_mock_plex_client(movies)

        from complexionist.tmdb import TMDBNotFoundError

        def get_movie(movie_id: int) -> TMDBMovieDetails:
            if movie_id == 200:
                raise TMDBNotFoundError("Not found")
            collection_id = 1
            return TMDBMovieDetails(
                id=movie_id,
                title=f"Movie {movie_id}",
                belongs_to_collection={"id": collection_id, "name": "Col 1"},
            )

        tmdb = MagicMock()
        tmdb.get_movie.side_effect = get_movie
        past = date(2020, 1, 1)
        tmdb.get_collection.return_value = TMDBCollection(
            id=1,
            name="Collection 1",
            parts=[
                TMDBMovie(id=100, title="Good Movie", release_date=past),
                TMDBMovie(id=300, title="Also Good", release_date=past),
                TMDBMovie(id=400, title="Missing Movie", release_date=past),
            ],
        )

        finder = MovieGapFinder(plex, tmdb)
        report = finder.find_gaps()

        assert report.movies_in_collections == 2
        assert report.unique_collections == 1

    def test_parallel_lookup_is_fast_with_cache(self) -> None:
        """When all lookups hit cache, the stagger delay should be skipped."""
        import time

        movies = [
            PlexMovie(rating_key=str(i), title=f"Movie {i}", tmdb_id=100 + i)
            for i in range(20)
        ]
        plex = self._create_mock_plex_client(movies)

        # All movies in collection 1
        movie_collections = {100 + i: 1 for i in range(20)}
        collections = {
            1: TMDBCollection(
                id=1,
                name="Big Collection",
                parts=[
                    TMDBMovie(id=100 + i, title=f"Movie {i}", release_date=date(2020, 1, 1))
                    for i in range(25)  # 20 owned + 5 missing
                ],
            ),
        }
        tmdb = self._create_mock_tmdb_client(movie_collections, collections)

        finder = MovieGapFinder(plex, tmdb)
        start = time.monotonic()
        report = finder.find_gaps()
        elapsed = time.monotonic() - start

        assert report.movies_in_collections == 20
        # With 20 movies and all cache hits (mocks return instantly),
        # should take well under 2 seconds. Without optimisation it
        # would take ~5s (20 * 0.25s stagger).
        assert elapsed < 2.0, f"Took {elapsed:.1f}s — stagger not skipped for cache hits?"


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

        def get_series_episodes(
            series_id: int, series_status: str | None = None
        ) -> list[TVDBEpisode]:
            return episodes_by_series.get(series_id, [])

        mock_client.get_series_episodes.side_effect = get_series_episodes
        mock_client.test_connection.return_value = True

        # Mock get_series to return an object with image and status attributes
        mock_series = MagicMock()
        mock_series.image = "https://example.com/poster.jpg"
        mock_series.status = "Continuing"
        mock_client.get_series.return_value = mock_series

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
                TVDBEpisode(
                    id=1,
                    seriesId=100,
                    seasonNumber=1,
                    number=1,
                    name="Pilot",
                    aired=date(2020, 1, 1),
                ),
                TVDBEpisode(
                    id=2,
                    seriesId=100,
                    seasonNumber=1,
                    number=2,
                    name="Second",
                    aired=date(2020, 1, 8),
                ),
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
                TVDBEpisode(
                    id=2, seriesId=100, seasonNumber=0, number=1, aired=date(2020, 1, 1)
                ),  # Special
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
                TVDBEpisode(
                    id=2,
                    seriesId=100,
                    seasonNumber=0,
                    number=1,
                    name="Special",
                    aired=date(2020, 1, 1),
                ),
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
                TVDBEpisode(
                    id=2, seriesId=100, seasonNumber=1, number=2, aired=date(2099, 12, 31)
                ),  # Future
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
                TVDBEpisode(
                    id=2,
                    seriesId=100,
                    seasonNumber=1,
                    number=2,
                    name="Future Ep",
                    aired=date(2099, 12, 31),
                ),
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

    def test_find_gaps_excluded_shows(self) -> None:
        """Test that excluded shows are skipped."""
        shows = [
            PlexShow(rating_key="1", title="Regular Show", tvdb_id=100),
            PlexShow(rating_key="2", title="Daily Talk Show", tvdb_id=200),
        ]
        plex_episodes = {
            "1": [
                PlexEpisode(rating_key="e1", title="Ep 1", season_number=1, episode_number=1),
            ],
            "2": [
                PlexEpisode(rating_key="e1", title="Ep 1", season_number=1, episode_number=1),
            ],
        }
        plex = self._create_mock_plex_client(shows, plex_episodes)

        tvdb_episodes = {
            100: [
                TVDBEpisode(id=1, seriesId=100, seasonNumber=1, number=1, aired=date(2020, 1, 1)),
                TVDBEpisode(id=2, seriesId=100, seasonNumber=1, number=2, aired=date(2020, 1, 8)),
            ],
            200: [
                TVDBEpisode(id=3, seriesId=200, seasonNumber=1, number=1, aired=date(2020, 1, 1)),
                TVDBEpisode(id=4, seriesId=200, seasonNumber=1, number=2, aired=date(2020, 1, 8)),
            ],
        }
        tvdb = self._create_mock_tvdb_client(tvdb_episodes)

        finder = EpisodeGapFinder(
            plex,
            tvdb,
            excluded_shows=["Daily Talk Show"],
        )
        report = finder.find_gaps()

        # Only "Regular Show" should be in results (missing 1 episode)
        assert len(report.shows_with_gaps) == 1
        assert report.shows_with_gaps[0].show_title == "Regular Show"

    def test_find_gaps_excluded_shows_case_insensitive(self) -> None:
        """Test that show exclusions are case-insensitive."""
        shows = [
            PlexShow(rating_key="1", title="Daily Talk Show", tvdb_id=100),
        ]
        plex_episodes = {
            "1": [
                PlexEpisode(rating_key="e1", title="Ep 1", season_number=1, episode_number=1),
            ],
        }
        plex = self._create_mock_plex_client(shows, plex_episodes)

        tvdb_episodes = {
            100: [
                TVDBEpisode(id=1, seriesId=100, seasonNumber=1, number=1, aired=date(2020, 1, 1)),
                TVDBEpisode(id=2, seriesId=100, seasonNumber=1, number=2, aired=date(2020, 1, 8)),
            ],
        }
        tvdb = self._create_mock_tvdb_client(tvdb_episodes)

        finder = EpisodeGapFinder(
            plex,
            tvdb,
            excluded_shows=["DAILY TALK SHOW"],  # Different case
        )
        report = finder.find_gaps()

        # Show should be excluded
        assert report.shows_with_tvdb_id == 0

    def test_find_gaps_recent_threshold(self) -> None:
        """Test that recently aired episodes are excluded.

        Note: This test can be flaky near midnight because the recent_threshold
        logic compares against midnight of the aired date, not the exact time.
        We skip the test if we're within the first 2 hours of the day to avoid
        false failures.
        """
        from datetime import datetime

        # Skip if we're within first 2 hours of the day (flaky zone)
        now = datetime.now()
        if now.hour < 2:
            import pytest

            pytest.skip("Skipping flaky test near midnight boundary")

        shows = [PlexShow(rating_key="1", title="Show", tvdb_id=100)]
        plex_episodes = {
            "1": [
                PlexEpisode(rating_key="e1", title="Ep 1", season_number=1, episode_number=1),
            ]
        }
        plex = self._create_mock_plex_client(shows, plex_episodes)

        # Use today's date - the episode aired "today" so should be excluded by 24h threshold
        # (since the filter checks if ep_datetime > recent_cutoff, and today's midnight
        # is typically within 24h of now, unless we're near midnight)
        today = date.today()
        old_date = date(2020, 1, 1)

        tvdb_episodes = {
            100: [
                TVDBEpisode(id=1, seriesId=100, seasonNumber=1, number=1, aired=old_date),
                TVDBEpisode(
                    id=2, seriesId=100, seasonNumber=1, number=2, name="Recent", aired=today
                ),
            ]
        }
        tvdb = self._create_mock_tvdb_client(tvdb_episodes)

        # With 24h threshold, today's episode should be excluded
        finder = EpisodeGapFinder(plex, tvdb, recent_threshold_hours=24)
        report = finder.find_gaps()

        # Should be complete (recent episode excluded)
        assert report.shows_with_gaps == []

    def test_find_gaps_recent_threshold_zero_includes_all(self) -> None:
        """Test that threshold of 0 includes all aired episodes."""
        shows = [PlexShow(rating_key="1", title="Show", tvdb_id=100)]
        plex_episodes = {
            "1": [
                PlexEpisode(rating_key="e1", title="Ep 1", season_number=1, episode_number=1),
            ]
        }
        plex = self._create_mock_plex_client(shows, plex_episodes)

        # Use yesterday's date - today is treated as "not yet aired" due to
        # timezone buffer, so we use yesterday to test the threshold=0 case
        yesterday = date.today() - timedelta(days=1)
        old_date = date(2020, 1, 1)

        tvdb_episodes = {
            100: [
                TVDBEpisode(id=1, seriesId=100, seasonNumber=1, number=1, aired=old_date),
                TVDBEpisode(
                    id=2, seriesId=100, seasonNumber=1, number=2, name="Recent", aired=yesterday
                ),
            ]
        }
        tvdb = self._create_mock_tvdb_client(tvdb_episodes)

        # With threshold=0, all aired episodes should be included
        finder = EpisodeGapFinder(plex, tvdb, recent_threshold_hours=0)
        report = finder.find_gaps()

        # Should show missing episode
        assert len(report.shows_with_gaps) == 1
        assert report.shows_with_gaps[0].missing_count == 1
