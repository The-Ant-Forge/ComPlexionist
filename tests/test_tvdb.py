"""Tests for the TVDB client."""

from datetime import date
from unittest.mock import MagicMock, patch

import pytest

from complexionist.tvdb import (
    TVDBAuthError,
    TVDBClient,
    TVDBEpisode,
    TVDBNotFoundError,
    TVDBRateLimitError,
    TVDBSeriesExtended,
)


class TestTVDBModels:
    """Tests for TVDB data models."""

    def test_episode_code(self) -> None:
        """Test episode code formatting."""
        ep = TVDBEpisode(
            id=1,
            seriesId=100,
            name="Pilot",
            seasonNumber=1,
            number=5,
        )
        assert ep.episode_code == "S01E05"

    def test_episode_is_aired_past(self) -> None:
        """Test is_aired for past episodes."""
        ep = TVDBEpisode(
            id=1,
            seriesId=100,
            seasonNumber=1,
            number=1,
            aired=date(2020, 1, 1),
        )
        assert ep.is_aired is True

    def test_episode_is_aired_future(self) -> None:
        """Test is_aired for future episodes."""
        ep = TVDBEpisode(
            id=1,
            seriesId=100,
            seasonNumber=1,
            number=1,
            aired=date(2099, 12, 31),
        )
        assert ep.is_aired is False

    def test_episode_is_aired_none(self) -> None:
        """Test is_aired when no air date."""
        ep = TVDBEpisode(
            id=1,
            seriesId=100,
            seasonNumber=1,
            number=1,
        )
        assert ep.is_aired is False

    def test_episode_is_special(self) -> None:
        """Test is_special for Season 0 episodes."""
        special = TVDBEpisode(id=1, seriesId=100, seasonNumber=0, number=1)
        regular = TVDBEpisode(id=2, seriesId=100, seasonNumber=1, number=1)

        assert special.is_special is True
        assert regular.is_special is False

    def test_series_extended_aired_episodes(self) -> None:
        """Test filtering aired episodes."""
        series = TVDBSeriesExtended(
            id=100,
            name="Test Show",
            episodes=[
                TVDBEpisode(id=1, seriesId=100, seasonNumber=1, number=1, aired=date(2020, 1, 1)),
                TVDBEpisode(id=2, seriesId=100, seasonNumber=1, number=2, aired=date(2099, 12, 31)),
                TVDBEpisode(id=3, seriesId=100, seasonNumber=1, number=3),
            ],
        )

        aired = series.aired_episodes
        assert len(aired) == 1
        assert aired[0].id == 1

    def test_series_extended_regular_episodes(self) -> None:
        """Test filtering non-special episodes."""
        series = TVDBSeriesExtended(
            id=100,
            name="Test Show",
            episodes=[
                TVDBEpisode(id=1, seriesId=100, seasonNumber=0, number=1),  # Special
                TVDBEpisode(id=2, seriesId=100, seasonNumber=1, number=1),
                TVDBEpisode(id=3, seriesId=100, seasonNumber=2, number=1),
            ],
        )

        regular = series.regular_episodes
        assert len(regular) == 2
        assert all(ep.season_number > 0 for ep in regular)

    def test_series_extended_episodes_by_season(self) -> None:
        """Test grouping episodes by season."""
        series = TVDBSeriesExtended(
            id=100,
            name="Test Show",
            episodes=[
                TVDBEpisode(id=1, seriesId=100, seasonNumber=1, number=1),
                TVDBEpisode(id=2, seriesId=100, seasonNumber=1, number=2),
                TVDBEpisode(id=3, seriesId=100, seasonNumber=2, number=1),
            ],
        )

        by_season = series.episodes_by_season()
        assert len(by_season) == 2
        assert len(by_season[1]) == 2
        assert len(by_season[2]) == 1


class TestTVDBClient:
    """Tests for TVDB API client."""

    def test_init_no_api_key(self) -> None:
        """Test initialization without API key raises error."""
        with pytest.raises(TVDBAuthError, match="API key not provided"):
            TVDBClient()

    def test_init_with_parameter(self) -> None:
        """Test initialization with parameter."""
        client = TVDBClient(api_key="direct_key")
        assert client.api_key == "direct_key"

    @patch("complexionist.tvdb.client.httpx.Client")
    def test_login_success(self, mock_client_class: MagicMock) -> None:
        """Test successful login flow."""
        # Mock the login response
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"data": {"token": "test_token_123"}}

        mock_client = MagicMock()
        mock_client.post.return_value = mock_response
        mock_client.__enter__ = MagicMock(return_value=mock_client)
        mock_client.__exit__ = MagicMock(return_value=False)

        with patch("complexionist.tvdb.client.httpx.Client", return_value=mock_client):
            client = TVDBClient(api_key="test_key")
            client._login()

            assert client._token == "test_token_123"

    @patch("complexionist.tvdb.client.httpx.Client")
    def test_login_invalid_key(self, mock_client_class: MagicMock) -> None:
        """Test login with invalid API key."""
        mock_response = MagicMock()
        mock_response.status_code = 401

        mock_client = MagicMock()
        mock_client.post.return_value = mock_response
        mock_client.__enter__ = MagicMock(return_value=mock_client)
        mock_client.__exit__ = MagicMock(return_value=False)

        with patch("complexionist.tvdb.client.httpx.Client", return_value=mock_client):
            client = TVDBClient(api_key="bad_key")

            with pytest.raises(TVDBAuthError, match="Invalid TVDB API key"):
                client._login()

    def test_handle_401_error(self) -> None:
        """Test 401 error handling."""
        client = TVDBClient(api_key="test_key")

        mock_response = MagicMock()
        mock_response.status_code = 401

        with pytest.raises(TVDBAuthError):
            client._handle_response(mock_response)

    def test_handle_404_error(self) -> None:
        """Test 404 error handling."""
        client = TVDBClient(api_key="test_key")

        mock_response = MagicMock()
        mock_response.status_code = 404

        with pytest.raises(TVDBNotFoundError):
            client._handle_response(mock_response)

    def test_handle_429_rate_limit(self) -> None:
        """Test 429 rate limit handling."""
        client = TVDBClient(api_key="test_key")

        mock_response = MagicMock()
        mock_response.status_code = 429
        mock_response.headers = {"Retry-After": "30"}

        with pytest.raises(TVDBRateLimitError) as exc_info:
            client._handle_response(mock_response)

        assert exc_info.value.retry_after == 30

    @patch("complexionist.tvdb.client.httpx.Client")
    def test_get_series_episodes_pagination(self, mock_client_class: MagicMock) -> None:
        """Test episode fetching with pagination."""
        client = TVDBClient(api_key="test_key")
        client._token = "test_token"

        # Mock responses for two pages
        page1_response = MagicMock()
        page1_response.status_code = 200
        page1_response.json.return_value = {
            "data": {
                "episodes": [
                    {"id": 1, "seriesId": 100, "seasonNumber": 1, "number": 1},
                    {"id": 2, "seriesId": 100, "seasonNumber": 1, "number": 2},
                ]
            }
        }

        mock_http_client = MagicMock()
        mock_http_client.get.return_value = page1_response
        mock_client_class.return_value = mock_http_client

        episodes = client.get_series_episodes(100)

        assert len(episodes) == 2
        assert episodes[0].episode_number == 1
        assert episodes[1].episode_number == 2

    def test_parse_date_valid(self) -> None:
        """Test parsing valid date string."""
        client = TVDBClient(api_key="test_key")
        result = client._parse_date("2020-05-15")
        assert result == date(2020, 5, 15)

    def test_parse_date_invalid(self) -> None:
        """Test parsing invalid date string."""
        client = TVDBClient(api_key="test_key")
        result = client._parse_date("not-a-date")
        assert result is None

    def test_parse_date_none(self) -> None:
        """Test parsing None date."""
        client = TVDBClient(api_key="test_key")
        result = client._parse_date(None)
        assert result is None
