"""Movie gap detection logic."""

import time
from collections.abc import Callable
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import date

from complexionist.gaps.models import CollectionGap, MissingMovie, MovieGapReport, OwnedMovie
from complexionist.plex import PlexClient, PlexMovie
from complexionist.tmdb import (
    TMDBClient,
    TMDBCollection,
    TMDBError,
    TMDBNotFoundError,
    TMDBRateLimitError,
)
from complexionist.utils import retry_with_backoff


class MovieGapFinder:
    """Find missing movies from collections in a Plex library."""

    def __init__(
        self,
        plex_client: PlexClient,
        tmdb_client: TMDBClient,
        include_future: bool = False,
        min_collection_size: int = 2,
        min_owned: int = 2,
        excluded_collections: list[str] | None = None,
        ignored_collection_ids: list[int] | None = None,
        progress_callback: Callable[[str, int, int], None] | None = None,
    ) -> None:
        """Initialize the gap finder.

        Args:
            plex_client: Connected Plex client.
            tmdb_client: Configured TMDB client.
            include_future: Include unreleased movies in results.
            min_collection_size: Only report collections with this many total
                movies or more. Default is 2.
            min_owned: Only report collections where you own at least this many
                movies. Default is 2 (prevents noise from single-movie matches).
            excluded_collections: List of collection names to skip.
            ignored_collection_ids: List of TMDB collection IDs to skip.
            progress_callback: Optional callback for progress updates.
                Signature: (stage: str, current: int, total: int)
        """
        self.plex = plex_client
        self.tmdb = tmdb_client
        self.include_future = include_future
        self.min_collection_size = min_collection_size
        self.min_owned = min_owned
        self.excluded_collections = {c.lower() for c in (excluded_collections or [])}
        self.ignored_collection_ids = set(ignored_collection_ids or [])
        self._progress = progress_callback or (lambda *args: None)

    def find_gaps(self, library_name: str | None = None) -> MovieGapReport:
        """Find all missing movies from collections.

        Args:
            library_name: Plex library name. If None, uses first movie library.

        Returns:
            Report with all collection gaps.
        """
        # Step 1: Get all movies from Plex
        self._progress("Loading movie library from Plex...", 0, 0)
        plex_movies = self.plex.get_movies(library_name, progress_callback=self._progress)

        # Determine library name and locations for report
        library_locations: list[str] = []
        if library_name is None:
            movie_libs = self.plex.get_movie_libraries()
            if movie_libs:
                lib_name = movie_libs[0].title
                library_locations = movie_libs[0].locations
            else:
                lib_name = "Movies"
        else:
            lib_name = library_name
            # Find the library to get its locations
            movie_libs = self.plex.get_movie_libraries()
            for lib in movie_libs:
                if lib.title == library_name:
                    library_locations = lib.locations
                    break

        # Step 2: Build owned movie set (by TMDB ID) and file path mapping
        movies_with_tmdb = [m for m in plex_movies if m.has_tmdb_id]
        owned_tmdb_ids: set[int] = {m.tmdb_id for m in movies_with_tmdb if m.tmdb_id}
        tmdb_to_file_path: dict[int, str | None] = {
            m.tmdb_id: m.file_path for m in movies_with_tmdb if m.tmdb_id
        }

        # Step 3: Query TMDB for collection membership
        collection_ids = self._get_collection_ids(movies_with_tmdb)

        # Step 4: Fetch full collections and find gaps
        gaps = self._find_collection_gaps(
            collection_ids, owned_tmdb_ids, tmdb_to_file_path, library_locations
        )

        # Sort: incomplete collections first (by missing count desc),
        # then complete-but-disorganized collections (alphabetically)
        gaps.sort(key=lambda g: (g.is_complete, -g.missing_count, g.collection_name))

        return MovieGapReport(
            library_name=lib_name,
            total_movies_scanned=len(plex_movies),
            movies_with_tmdb_id=len(movies_with_tmdb),
            movies_in_collections=len(collection_ids),
            unique_collections=len(set(collection_ids.values())),
            collections_with_gaps=gaps,
        )

    def _get_collection_ids(self, movies: list[PlexMovie]) -> dict[int, int]:
        """Get collection IDs for movies that belong to collections.

        Uses 2 parallel workers to speed up TMDB lookups, with slight
        stagger between submissions to avoid rate-limit bursts.

        Args:
            movies: List of Plex movies with TMDB IDs.

        Returns:
            Dict mapping movie TMDB ID to collection ID.
        """
        movies_with_ids = [m for m in movies if m.tmdb_id is not None]
        total = len(movies_with_ids)
        if total == 0:
            return {}

        collection_map: dict[int, int] = {}
        completed = 0

        def lookup_movie(movie: PlexMovie) -> tuple[int | None, int | None, str]:
            """Look up a single movie's collection ID. Returns (tmdb_id, collection_id, title)."""
            try:
                collection_id = self._get_movie_collection_id(movie.tmdb_id)  # type: ignore[arg-type]
                return (movie.tmdb_id, collection_id, movie.title)
            except TMDBNotFoundError:
                return (movie.tmdb_id, None, movie.title)
            except TMDBError as e:
                from complexionist.gui.errors import log_error

                log_error(e, f"TMDB API error for movie: {movie.title}")
                return (movie.tmdb_id, None, movie.title)

        with ThreadPoolExecutor(max_workers=2) as executor:
            # Submit all tasks with adaptive stagger: only delay if this movie
            # will be a cache miss (real API call). Cache hits are instant and
            # don't need rate-limit throttling.
            futures = {}
            for i, movie in enumerate(movies_with_ids):
                future = executor.submit(lookup_movie, movie)
                futures[future] = i
                # Only stagger if this movie will be a cache miss (real API call).
                # Cache hits are instant and don't need rate-limit throttling.
                if i < total - 1 and not self._is_movie_cached(movie.tmdb_id):  # type: ignore[arg-type]
                    time.sleep(0.25)

            # Collect results as they complete
            for future in as_completed(futures):
                completed += 1
                tmdb_id, collection_id, title = future.result()
                self._progress(f"Checking: {title}", completed, total)
                if tmdb_id is not None and collection_id is not None:
                    collection_map[tmdb_id] = collection_id

        return collection_map

    def _is_movie_cached(self, tmdb_id: int) -> bool:
        """Check if a movie's TMDB data is already in the cache."""
        if self.tmdb._cache is None:
            return False
        return self.tmdb._cache.get("tmdb", "movies", str(tmdb_id)) is not None

    @retry_with_backoff(
        max_retries=3,
        base_delay=1.0,
        retry_on=(TMDBRateLimitError,),
    )
    def _get_movie_collection_id(self, tmdb_id: int) -> int | None:
        """Get the collection ID for a movie.

        Args:
            tmdb_id: TMDB movie ID.

        Returns:
            Collection ID if the movie belongs to one, None otherwise.
        """
        movie_details = self.tmdb.get_movie(tmdb_id)
        return movie_details.collection_id

    def _find_collection_gaps(
        self,
        movie_collections: dict[int, int],
        owned_tmdb_ids: set[int],
        tmdb_to_file_path: dict[int, str | None],
        library_locations: list[str],
    ) -> list[CollectionGap]:
        """Find gaps in collections.

        Args:
            movie_collections: Map of movie TMDB ID to collection ID.
            owned_tmdb_ids: Set of owned movie TMDB IDs.
            tmdb_to_file_path: Map of TMDB ID to file path.
            library_locations: Plex library folder paths.

        Returns:
            List of collection gaps (only collections with missing movies).
        """
        # Get unique collection IDs
        unique_collection_ids = set(movie_collections.values())
        total = len(unique_collection_ids)
        gaps: list[CollectionGap] = []

        for i, collection_id in enumerate(unique_collection_ids):
            # Skip ignored collections (by ID)
            if collection_id in self.ignored_collection_ids:
                self._progress("Analyzing: (skipped)", i + 1, total)
                continue

            try:
                collection = self._fetch_collection(collection_id)
                self._progress(f"Analyzing: {collection.name}", i + 1, total)
            except TMDBNotFoundError:
                continue
            except TMDBError as e:
                # Log API errors and continue with next collection
                from complexionist.gui.errors import log_error

                log_error(e, f"TMDB API error for collection ID: {collection_id}")
                continue
            except Exception as e:
                # Log unexpected errors and continue
                from complexionist.gui.errors import log_error

                log_error(e, f"Unexpected error processing collection ID: {collection_id}")
                continue

            # Skip excluded collections (by name)
            if collection.name.lower() in self.excluded_collections:
                continue

            # Get movies to consider (released or all if include_future)
            if self.include_future:
                movies_to_check = collection.parts
            else:
                movies_to_check = collection.released_movies

            # Skip small collections
            if len(movies_to_check) < self.min_collection_size:
                continue

            # Find missing movies
            collection_movie_ids = {m.id for m in movies_to_check}
            owned_in_collection = owned_tmdb_ids & collection_movie_ids
            missing_ids = collection_movie_ids - owned_tmdb_ids

            if not missing_ids:
                # Collection is complete — check if it needs organizing
                owned_movies_list = [
                    OwnedMovie(
                        tmdb_id=m.id,
                        title=m.title,
                        year=m.year,
                        file_path=tmdb_to_file_path.get(m.id),
                    )
                    for m in movies_to_check
                    if m.id in owned_in_collection
                ]
                owned_movies_list.sort(key=lambda m: m.year or 9999)

                gap = CollectionGap(
                    collection_id=collection_id,
                    collection_name=collection.name,
                    total_movies=len(movies_to_check),
                    owned_movies=len(owned_in_collection),
                    poster_path=collection.poster_path,
                    owned_movie_list=owned_movies_list,
                    missing_movies=[],
                    library_locations=library_locations,
                    is_complete=True,
                )

                if gap.movies_in_different_folders:
                    gaps.append(gap)
                continue

            # Skip collections where user doesn't own enough movies
            # (prevents noise from single-movie matches)
            if len(owned_in_collection) < self.min_owned:
                continue

            # Build owned movie list
            owned_movies_list = [
                OwnedMovie(
                    tmdb_id=m.id,
                    title=m.title,
                    year=m.year,
                    file_path=tmdb_to_file_path.get(m.id),
                )
                for m in movies_to_check
                if m.id in owned_in_collection
            ]
            # Sort by release date (oldest first)
            owned_movies_list.sort(key=lambda m: m.year or 9999)

            # Build missing movie list
            missing_movies = [
                MissingMovie(
                    tmdb_id=m.id,
                    title=m.title,
                    release_date=m.release_date,
                    year=m.year,
                )
                for m in movies_to_check
                if m.id in missing_ids
            ]

            # Sort by release date (oldest first)
            missing_movies.sort(key=lambda m: m.release_date or date(9999, 12, 31))

            gaps.append(
                CollectionGap(
                    collection_id=collection_id,
                    collection_name=collection.name,
                    total_movies=len(movies_to_check),
                    owned_movies=len(owned_in_collection),
                    poster_path=collection.poster_path,
                    owned_movie_list=owned_movies_list,
                    missing_movies=missing_movies,
                    library_locations=library_locations,
                )
            )

        return gaps

    @retry_with_backoff(
        max_retries=3,
        base_delay=1.0,
        retry_on=(TMDBRateLimitError,),
    )
    def _fetch_collection(self, collection_id: int) -> TMDBCollection:
        """Fetch a collection from TMDB with retry.

        Args:
            collection_id: TMDB collection ID.

        Returns:
            The collection with all movies.
        """
        return self.tmdb.get_collection(collection_id)
