"""Plex Media Server client."""

import os
import re
from urllib.parse import urlparse

from plexapi.exceptions import BadRequest, NotFound, Unauthorized
from plexapi.server import PlexServer

from complexionist.plex.models import (
    PlexEpisode,
    PlexLibrary,
    PlexMovie,
    PlexShow,
    PlexShowWithEpisodes,
)


class PlexError(Exception):
    """Base exception for Plex errors."""

    pass


class PlexAuthError(PlexError):
    """Authentication error."""

    pass


class PlexConnectionError(PlexError):
    """Connection error."""

    pass


class PlexNotFoundError(PlexError):
    """Resource not found."""

    pass


class PlexClient:
    """Client for Plex Media Server."""

    def __init__(
        self,
        url: str | None = None,
        token: str | None = None,
        timeout: int = 30,
    ) -> None:
        """Initialize the Plex client.

        Args:
            url: Plex server URL. If not provided, reads from PLEX_URL env var.
            token: Plex auth token. If not provided, reads from PLEX_TOKEN env var.
            timeout: Request timeout in seconds.
        """
        self.url = url or os.environ.get("PLEX_URL")
        self.token = token or os.environ.get("PLEX_TOKEN")

        if not self.url:
            raise PlexAuthError(
                "Plex server URL not provided. Set PLEX_URL environment variable "
                "or pass url parameter."
            )

        if not self.token:
            raise PlexAuthError(
                "Plex token not provided. Set PLEX_TOKEN environment variable "
                "or pass token parameter."
            )

        # Normalize URL
        self.url = self._normalize_url(self.url)

        self._timeout = timeout
        self._server: PlexServer | None = None

    def _normalize_url(self, url: str) -> str:
        """Normalize the Plex server URL."""
        # urlparse treats "localhost:32400" as scheme="localhost", path="32400"
        # We need to check if it looks like a real scheme (http/https)
        parsed = urlparse(url)
        if parsed.scheme not in ("http", "https"):
            url = f"http://{url}"
        return url.rstrip("/")

    def connect(self) -> None:
        """Connect to the Plex server.

        Raises:
            PlexAuthError: If authentication fails.
            PlexConnectionError: If connection fails.
        """
        try:
            self._server = PlexServer(self.url, self.token, timeout=self._timeout)
        except Unauthorized as e:
            raise PlexAuthError(f"Invalid Plex token: {e}") from e
        except Exception as e:
            raise PlexConnectionError(f"Failed to connect to Plex server: {e}") from e

    @property
    def server(self) -> PlexServer:
        """Get the connected server, connecting if necessary."""
        if self._server is None:
            self.connect()
        return self._server  # type: ignore[return-value]

    @property
    def server_name(self) -> str:
        """Get the server's friendly name."""
        return self.server.friendlyName

    def __enter__(self) -> "PlexClient":
        self.connect()
        return self

    def __exit__(self, *args: object) -> None:
        pass  # PlexServer doesn't need explicit cleanup

    def test_connection(self) -> bool:
        """Test the connection to the Plex server.

        Returns:
            True if connection is successful.

        Raises:
            PlexAuthError: If authentication fails.
            PlexConnectionError: If connection fails.
        """
        _ = self.server  # Will raise if connection fails
        return True

    def get_libraries(self) -> list[PlexLibrary]:
        """Get all library sections.

        Returns:
            List of library sections.
        """
        sections = self.server.library.sections()
        return [
            PlexLibrary(
                key=str(section.key),
                title=section.title,
                type=section.type,
            )
            for section in sections
        ]

    def get_movie_libraries(self) -> list[PlexLibrary]:
        """Get all movie libraries."""
        return [lib for lib in self.get_libraries() if lib.is_movie_library]

    def get_tv_libraries(self) -> list[PlexLibrary]:
        """Get all TV show libraries."""
        return [lib for lib in self.get_libraries() if lib.is_tv_library]

    def _extract_external_ids(self, item: object) -> dict[str, int | str | None]:
        """Extract external IDs (TMDB, TVDB, IMDB) from a Plex item."""
        tmdb_id = None
        tvdb_id = None
        imdb_id = None

        # Try to get GUIDs from the item
        guids = getattr(item, "guids", []) or []

        for guid in guids:
            guid_str = str(guid.id) if hasattr(guid, "id") else str(guid)

            # TMDB
            if "tmdb://" in guid_str:
                match = re.search(r"tmdb://(\d+)", guid_str)
                if match:
                    tmdb_id = int(match.group(1))

            # TVDB
            elif "tvdb://" in guid_str:
                match = re.search(r"tvdb://(\d+)", guid_str)
                if match:
                    tvdb_id = int(match.group(1))

            # IMDB
            elif "imdb://" in guid_str:
                match = re.search(r"imdb://(tt\d+)", guid_str)
                if match:
                    imdb_id = match.group(1)

        return {
            "tmdb_id": tmdb_id,
            "tvdb_id": tvdb_id,
            "imdb_id": imdb_id,
        }

    def get_movies(self, library_name: str | None = None) -> list[PlexMovie]:
        """Get all movies from a library.

        Args:
            library_name: Name of the movie library. If None, uses the first movie library.

        Returns:
            List of movies with external IDs.

        Raises:
            PlexNotFoundError: If the library is not found.
        """
        # Find the library
        if library_name:
            try:
                section = self.server.library.section(library_name)
            except NotFound as e:
                raise PlexNotFoundError(f"Library '{library_name}' not found") from e
        else:
            movie_libs = self.get_movie_libraries()
            if not movie_libs:
                raise PlexNotFoundError("No movie libraries found")
            section = self.server.library.section(movie_libs[0].title)

        # Get all movies
        movies = []
        for item in section.all():
            external_ids = self._extract_external_ids(item)

            movie = PlexMovie(
                rating_key=str(item.ratingKey),
                title=item.title,
                year=getattr(item, "year", None),
                tmdb_id=external_ids["tmdb_id"],  # type: ignore[arg-type]
                imdb_id=external_ids["imdb_id"],  # type: ignore[arg-type]
                guid=str(item.guid) if hasattr(item, "guid") else "",
            )
            movies.append(movie)

        return movies

    def get_shows(self, library_name: str | None = None) -> list[PlexShow]:
        """Get all TV shows from a library.

        Args:
            library_name: Name of the TV library. If None, uses the first TV library.

        Returns:
            List of TV shows with external IDs.

        Raises:
            PlexNotFoundError: If the library is not found.
        """
        # Find the library
        if library_name:
            try:
                section = self.server.library.section(library_name)
            except NotFound as e:
                raise PlexNotFoundError(f"Library '{library_name}' not found") from e
        else:
            tv_libs = self.get_tv_libraries()
            if not tv_libs:
                raise PlexNotFoundError("No TV libraries found")
            section = self.server.library.section(tv_libs[0].title)

        # Get all shows
        shows = []
        for item in section.all():
            external_ids = self._extract_external_ids(item)

            show = PlexShow(
                rating_key=str(item.ratingKey),
                title=item.title,
                year=getattr(item, "year", None),
                tvdb_id=external_ids["tvdb_id"],  # type: ignore[arg-type]
                tmdb_id=external_ids["tmdb_id"],  # type: ignore[arg-type]
                imdb_id=external_ids["imdb_id"],  # type: ignore[arg-type]
                guid=str(item.guid) if hasattr(item, "guid") else "",
            )
            shows.append(show)

        return shows

    def get_episodes(self, show_rating_key: str) -> list[PlexEpisode]:
        """Get all episodes for a TV show.

        Args:
            show_rating_key: The rating key of the TV show.

        Returns:
            List of episodes.
        """
        try:
            show = self.server.fetchItem(int(show_rating_key))
        except (NotFound, BadRequest) as e:
            raise PlexNotFoundError(f"Show not found: {show_rating_key}") from e

        episodes = []
        for episode in show.episodes():
            # Get file path if available
            file_path = None
            if hasattr(episode, "media") and episode.media:
                for media in episode.media:
                    if hasattr(media, "parts") and media.parts:
                        for part in media.parts:
                            if hasattr(part, "file"):
                                file_path = part.file
                                break
                    if file_path:
                        break

            ep = PlexEpisode(
                rating_key=str(episode.ratingKey),
                title=episode.title or "",
                season_number=episode.parentIndex or 0,
                episode_number=episode.index or 0,
                show_title=show.title,
                file_path=file_path,
            )
            episodes.append(ep)

        return episodes

    def get_show_with_episodes(self, show_rating_key: str) -> PlexShowWithEpisodes:
        """Get a TV show with all its episodes.

        Args:
            show_rating_key: The rating key of the TV show.

        Returns:
            Show with all episodes.
        """
        try:
            show_item = self.server.fetchItem(int(show_rating_key))
        except (NotFound, BadRequest) as e:
            raise PlexNotFoundError(f"Show not found: {show_rating_key}") from e

        external_ids = self._extract_external_ids(show_item)

        show = PlexShow(
            rating_key=str(show_item.ratingKey),
            title=show_item.title,
            year=getattr(show_item, "year", None),
            tvdb_id=external_ids["tvdb_id"],  # type: ignore[arg-type]
            tmdb_id=external_ids["tmdb_id"],  # type: ignore[arg-type]
            imdb_id=external_ids["imdb_id"],  # type: ignore[arg-type]
            guid=str(show_item.guid) if hasattr(show_item, "guid") else "",
        )

        episodes = self.get_episodes(show_rating_key)

        return PlexShowWithEpisodes(show=show, episodes=episodes)

    def get_all_shows_with_episodes(
        self, library_name: str | None = None
    ) -> list[PlexShowWithEpisodes]:
        """Get all TV shows with their episodes from a library.

        Args:
            library_name: Name of the TV library. If None, uses the first TV library.

        Returns:
            List of shows with all their episodes.
        """
        shows = self.get_shows(library_name)
        result = []

        for show in shows:
            show_with_episodes = PlexShowWithEpisodes(
                show=show,
                episodes=self.get_episodes(show.rating_key),
            )
            result.append(show_with_episodes)

        return result
