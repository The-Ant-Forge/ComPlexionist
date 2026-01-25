"""Tests for the Plex client."""

from unittest.mock import MagicMock, patch

import pytest

from complexionist.plex import (
    PlexAuthError,
    PlexClient,
    PlexEpisode,
    PlexLibrary,
    PlexMovie,
    PlexShow,
    PlexShowWithEpisodes,
)


class TestPlexModels:
    """Tests for Plex data models."""

    def test_library_is_movie(self) -> None:
        """Test movie library detection."""
        lib = PlexLibrary(key="1", title="Movies", type="movie")
        assert lib.is_movie_library is True
        assert lib.is_tv_library is False

    def test_library_is_tv(self) -> None:
        """Test TV library detection."""
        lib = PlexLibrary(key="2", title="TV Shows", type="show")
        assert lib.is_movie_library is False
        assert lib.is_tv_library is True

    def test_movie_has_tmdb_id(self) -> None:
        """Test movie TMDB ID detection."""
        movie_with = PlexMovie(rating_key="1", title="Test", tmdb_id=123)
        movie_without = PlexMovie(rating_key="2", title="Test2")

        assert movie_with.has_tmdb_id is True
        assert movie_without.has_tmdb_id is False

    def test_show_has_tvdb_id(self) -> None:
        """Test show TVDB ID detection."""
        show_with = PlexShow(rating_key="1", title="Test", tvdb_id=456)
        show_without = PlexShow(rating_key="2", title="Test2")

        assert show_with.has_tvdb_id is True
        assert show_without.has_tvdb_id is False

    def test_episode_code(self) -> None:
        """Test episode code formatting."""
        ep = PlexEpisode(
            rating_key="1",
            title="Pilot",
            season_number=1,
            episode_number=5,
        )
        assert ep.episode_code == "S01E05"

    def test_show_with_episodes_seasons(self) -> None:
        """Test episode grouping by season."""
        show = PlexShow(rating_key="1", title="Test Show")
        episodes = [
            PlexEpisode(rating_key="1", title="Ep1", season_number=1, episode_number=1),
            PlexEpisode(rating_key="2", title="Ep2", season_number=1, episode_number=2),
            PlexEpisode(rating_key="3", title="Ep3", season_number=2, episode_number=1),
        ]
        show_with_eps = PlexShowWithEpisodes(show=show, episodes=episodes)

        seasons = show_with_eps.seasons
        assert len(seasons) == 2
        assert len(seasons[1]) == 2
        assert len(seasons[2]) == 1

    def test_show_episode_numbers_by_season(self) -> None:
        """Test episode number extraction by season."""
        show = PlexShow(rating_key="1", title="Test Show")
        episodes = [
            PlexEpisode(rating_key="1", title="Ep1", season_number=1, episode_number=1),
            PlexEpisode(rating_key="2", title="Ep2", season_number=1, episode_number=3),
            PlexEpisode(rating_key="3", title="Ep3", season_number=2, episode_number=1),
        ]
        show_with_eps = PlexShowWithEpisodes(show=show, episodes=episodes)

        ep_nums = show_with_eps.episode_numbers_by_season
        assert ep_nums[1] == {1, 3}
        assert ep_nums[2] == {1}


class TestPlexClient:
    """Tests for Plex API client."""

    def test_init_no_url(self) -> None:
        """Test initialization without URL raises error."""
        with patch.dict("os.environ", {}, clear=True):
            with pytest.raises(PlexAuthError, match="URL not provided"):
                PlexClient()

    def test_init_no_token(self) -> None:
        """Test initialization without token raises error."""
        with pytest.raises(PlexAuthError, match="token not provided"):
            PlexClient(url="http://localhost:32400")

    def test_init_with_parameters(self) -> None:
        """Test initialization with parameters."""
        client = PlexClient(url="http://plex.local:32400", token="direct_token")
        assert client.url == "http://plex.local:32400"
        assert client.token == "direct_token"

    def test_url_normalization(self) -> None:
        """Test URL normalization."""
        # Without scheme
        client1 = PlexClient(url="localhost:32400", token="test")
        assert client1.url == "http://localhost:32400"

        # With trailing slash
        client2 = PlexClient(url="http://localhost:32400/", token="test")
        assert client2.url == "http://localhost:32400"

    @patch("complexionist.plex.client.PlexServer")
    def test_connect_success(self, mock_server_class: MagicMock) -> None:
        """Test successful connection."""
        mock_server = MagicMock()
        mock_server.friendlyName = "Test Server"
        mock_server_class.return_value = mock_server

        client = PlexClient(url="http://localhost:32400", token="test")
        client.connect()

        assert client._server is mock_server
        mock_server_class.assert_called_once()

    @patch("complexionist.plex.client.PlexServer")
    def test_get_libraries(self, mock_server_class: MagicMock) -> None:
        """Test getting library sections."""
        # Create mock sections
        mock_movie_section = MagicMock()
        mock_movie_section.key = 1
        mock_movie_section.title = "Movies"
        mock_movie_section.type = "movie"

        mock_tv_section = MagicMock()
        mock_tv_section.key = 2
        mock_tv_section.title = "TV Shows"
        mock_tv_section.type = "show"

        mock_server = MagicMock()
        mock_server.library.sections.return_value = [mock_movie_section, mock_tv_section]
        mock_server_class.return_value = mock_server

        with PlexClient(url="http://localhost:32400", token="test") as client:
            libraries = client.get_libraries()

        assert len(libraries) == 2
        assert libraries[0].title == "Movies"
        assert libraries[0].is_movie_library is True
        assert libraries[1].title == "TV Shows"
        assert libraries[1].is_tv_library is True

    @patch("complexionist.plex.client.PlexServer")
    def test_extract_external_ids(self, mock_server_class: MagicMock) -> None:
        """Test extraction of external IDs from GUIDs."""
        mock_server_class.return_value = MagicMock()

        client = PlexClient(url="http://localhost:32400", token="test")

        # Create mock item with GUIDs
        mock_guid_tmdb = MagicMock()
        mock_guid_tmdb.id = "tmdb://348"

        mock_guid_imdb = MagicMock()
        mock_guid_imdb.id = "imdb://tt0078748"

        mock_guid_tvdb = MagicMock()
        mock_guid_tvdb.id = "tvdb://81189"

        mock_item = MagicMock()
        mock_item.guids = [mock_guid_tmdb, mock_guid_imdb, mock_guid_tvdb]

        ids = client._extract_external_ids(mock_item)

        assert ids["tmdb_id"] == 348
        assert ids["imdb_id"] == "tt0078748"
        assert ids["tvdb_id"] == 81189

    @patch("complexionist.plex.client.PlexServer")
    def test_get_movies(self, mock_server_class: MagicMock) -> None:
        """Test getting movies from a library."""
        # Create mock movie
        mock_guid = MagicMock()
        mock_guid.id = "tmdb://348"

        mock_movie = MagicMock()
        mock_movie.ratingKey = 12345
        mock_movie.title = "Alien"
        mock_movie.year = 1979
        mock_movie.guid = "plex://movie/abc123"
        mock_movie.guids = [mock_guid]

        mock_section = MagicMock()
        mock_section.all.return_value = [mock_movie]

        mock_server = MagicMock()
        mock_server.library.section.return_value = mock_section

        # Mock get_movie_libraries to return a library
        mock_movie_lib = MagicMock()
        mock_movie_lib.key = 1
        mock_movie_lib.title = "Movies"
        mock_movie_lib.type = "movie"
        mock_server.library.sections.return_value = [mock_movie_lib]

        mock_server_class.return_value = mock_server

        with PlexClient(url="http://localhost:32400", token="test") as client:
            movies = client.get_movies()

        assert len(movies) == 1
        assert movies[0].title == "Alien"
        assert movies[0].year == 1979
        assert movies[0].tmdb_id == 348

    @patch("complexionist.plex.client.PlexServer")
    def test_get_episodes(self, mock_server_class: MagicMock) -> None:
        """Test getting episodes for a show."""
        # Create mock episodes
        mock_part = MagicMock()
        mock_part.file = "/media/tv/show/s01e01.mkv"

        mock_media = MagicMock()
        mock_media.parts = [mock_part]

        mock_ep1 = MagicMock()
        mock_ep1.ratingKey = 100
        mock_ep1.title = "Pilot"
        mock_ep1.parentIndex = 1  # season
        mock_ep1.index = 1  # episode
        mock_ep1.media = [mock_media]

        mock_ep2 = MagicMock()
        mock_ep2.ratingKey = 101
        mock_ep2.title = "Episode 2"
        mock_ep2.parentIndex = 1
        mock_ep2.index = 2
        mock_ep2.media = []

        mock_show = MagicMock()
        mock_show.title = "Test Show"
        mock_show.episodes.return_value = [mock_ep1, mock_ep2]

        mock_server = MagicMock()
        mock_server.fetchItem.return_value = mock_show
        mock_server_class.return_value = mock_server

        with PlexClient(url="http://localhost:32400", token="test") as client:
            episodes = client.get_episodes("12345")

        assert len(episodes) == 2
        assert episodes[0].title == "Pilot"
        assert episodes[0].season_number == 1
        assert episodes[0].episode_number == 1
        assert episodes[0].file_path == "/media/tv/show/s01e01.mkv"
        assert episodes[1].file_path is None
