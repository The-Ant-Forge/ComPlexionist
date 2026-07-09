"""Tests for the TVDB client."""

from datetime import date, timedelta
from unittest.mock import MagicMock, patch

import httpx
import pytest

from complexionist.tvdb import (
    TVDBAuthError,
    TVDBClient,
    TVDBEpisode,
    TVDBError,
    TVDBNotFoundError,
    TVDBRateLimitError,
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

    def test_episode_is_aired_today(self) -> None:
        """Test is_aired for episode airing today — should be False (24h grace period)."""
        ep = TVDBEpisode(
            id=1,
            seriesId=100,
            seasonNumber=1,
            number=1,
            aired=date.today(),
        )
        assert ep.is_aired is False

    def test_episode_is_aired_yesterday(self) -> None:
        """Test is_aired for episode that aired yesterday — should be False (24h grace)."""
        ep = TVDBEpisode(
            id=1,
            seriesId=100,
            seasonNumber=1,
            number=1,
            aired=date.today() - timedelta(days=1),
        )
        assert ep.is_aired is False

    def test_episode_is_aired_two_days_ago(self) -> None:
        """Test is_aired for episode that aired 2 days ago — should be True."""
        ep = TVDBEpisode(
            id=1,
            seriesId=100,
            seasonNumber=1,
            number=1,
            aired=date.today() - timedelta(days=2),
        )
        assert ep.is_aired is True

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


class TestTVDBClient:
    """Tests for TVDB API client."""

    def test_init_no_api_key(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """Test initialization without API key raises error."""
        # Pin an empty config so neither a cached config nor a real
        # complexionist.ini in the working directory leaks in.
        import complexionist.config as config_mod

        monkeypatch.setattr(config_mod, "_config", config_mod.AppConfig())
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

    def test_login_wraps_transport_error(self) -> None:
        """A network blip during login surfaces as TVDBError, not raw httpx."""
        mock_client = MagicMock()
        mock_client.post.side_effect = httpx.ConnectError("no route to host")
        mock_client.__enter__ = MagicMock(return_value=mock_client)
        mock_client.__exit__ = MagicMock(return_value=False)

        with patch("complexionist.tvdb.client.httpx.Client", return_value=mock_client):
            client = TVDBClient(api_key="test_key")

            with pytest.raises(TVDBError):
                client.login()

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
