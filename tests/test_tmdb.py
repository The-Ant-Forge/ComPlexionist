"""Tests for the TMDB client."""

from datetime import date
from unittest.mock import MagicMock, patch

import pytest

from complexionist.tmdb import (
    TMDBAuthError,
    TMDBClient,
    TMDBCollection,
    TMDBMovie,
    TMDBMovieDetails,
    TMDBNotFoundError,
    TMDBRateLimitError,
)

# Sample API responses
MOVIE_RESPONSE = {
    "id": 348,
    "title": "Alien",
    "release_date": "1979-05-25",
    "overview": "During its return to the earth...",
    "poster_path": "/vfrQk5IPloGg1v9Rzbh2Eg3VGyM.jpg",
    "belongs_to_collection": {
        "id": 8091,
        "name": "Alien Collection",
        "poster_path": "/uVcmvfMHtQrLPXUPFQfpJQwHRXy.jpg",
        "backdrop_path": "/2GqEdrmqpqPh1k7IQ9NWlAtLPSV.jpg",
    },
}

MOVIE_NO_COLLECTION_RESPONSE = {
    "id": 550,
    "title": "Fight Club",
    "release_date": "1999-10-15",
    "overview": "A ticking-Loss clerk...",
    "poster_path": "/poster.jpg",
    "belongs_to_collection": None,
}

COLLECTION_RESPONSE = {
    "id": 8091,
    "name": "Alien Collection",
    "overview": "A science fiction horror film series...",
    "poster_path": "/uVcmvfMHtQrLPXUPFQfpJQwHRXy.jpg",
    "backdrop_path": "/2GqEdrmqpqPh1k7IQ9NWlAtLPSV.jpg",
    "parts": [
        {
            "id": 348,
            "title": "Alien",
            "release_date": "1979-05-25",
            "overview": "During its return...",
            "poster_path": "/poster1.jpg",
        },
        {
            "id": 679,
            "title": "Aliens",
            "release_date": "1986-07-18",
            "overview": "Ellen Ripley is rescued...",
            "poster_path": "/poster2.jpg",
        },
        {
            "id": 999999,
            "title": "Alien: Future",
            "release_date": "2030-01-01",
            "overview": "Future alien movie...",
            "poster_path": "/poster3.jpg",
        },
    ],
}


class TestTMDBModels:
    """Tests for TMDB data models."""

    def test_movie_year(self) -> None:
        """Test movie year property."""
        movie = TMDBMovie(id=1, title="Test", release_date=date(2020, 5, 15))
        assert movie.year == 2020

    def test_movie_year_none(self) -> None:
        """Test movie year when no release date."""
        movie = TMDBMovie(id=1, title="Test", release_date=None)
        assert movie.year is None

    def test_movie_is_released(self) -> None:
        """Test movie is_released property."""
        past_movie = TMDBMovie(id=1, title="Past", release_date=date(2020, 1, 1))
        future_movie = TMDBMovie(id=2, title="Future", release_date=date(2030, 1, 1))
        no_date_movie = TMDBMovie(id=3, title="NoDate", release_date=None)

        assert past_movie.is_released is True
        assert future_movie.is_released is False
        assert no_date_movie.is_released is False

    def test_collection_released_movies(self) -> None:
        """Test collection released_movies property."""
        collection = TMDBCollection(
            id=1,
            name="Test Collection",
            parts=[
                TMDBMovie(id=1, title="Released", release_date=date(2020, 1, 1)),
                TMDBMovie(id=2, title="Future", release_date=date(2030, 1, 1)),
                TMDBMovie(id=3, title="NoDate", release_date=None),
            ],
        )

        released = collection.released_movies
        assert len(released) == 1
        assert released[0].title == "Released"


class TestTMDBClient:
    """Tests for TMDB API client."""

    def test_init_no_api_key(self) -> None:
        """Test initialization without API key raises error."""
        with pytest.raises(TMDBAuthError, match="API key not provided"):
            TMDBClient()

    def test_init_with_parameter(self) -> None:
        """Test initialization with parameter."""
        client = TMDBClient(api_key="direct_key")
        assert client.api_key == "direct_key"
        client.close()

    @patch("httpx.Client.get")
    def test_get_movie_with_collection(self, mock_get: MagicMock) -> None:
        """Test getting a movie that belongs to a collection."""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = MOVIE_RESPONSE
        mock_get.return_value = mock_response

        with TMDBClient(api_key="test") as client:
            movie = client.get_movie(348)

        assert isinstance(movie, TMDBMovieDetails)
        assert movie.id == 348
        assert movie.title == "Alien"
        assert movie.release_date == date(1979, 5, 25)
        assert movie.collection_id == 8091
        assert movie.collection_name == "Alien Collection"

    @patch("httpx.Client.get")
    def test_get_movie_without_collection(self, mock_get: MagicMock) -> None:
        """Test getting a movie that doesn't belong to a collection."""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = MOVIE_NO_COLLECTION_RESPONSE
        mock_get.return_value = mock_response

        with TMDBClient(api_key="test") as client:
            movie = client.get_movie(550)

        assert movie.collection_id is None
        assert movie.collection_name is None

    @patch("httpx.Client.get")
    def test_get_collection(self, mock_get: MagicMock) -> None:
        """Test getting a collection with all movies."""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = COLLECTION_RESPONSE
        mock_get.return_value = mock_response

        with TMDBClient(api_key="test") as client:
            collection = client.get_collection(8091)

        assert isinstance(collection, TMDBCollection)
        assert collection.id == 8091
        assert collection.name == "Alien Collection"
        assert collection.movie_count == 3
        assert len(collection.released_movies) == 2  # Excludes future movie

    @patch("httpx.Client.get")
    def test_handle_401_error(self, mock_get: MagicMock) -> None:
        """Test handling of 401 authentication error."""
        mock_response = MagicMock()
        mock_response.status_code = 401
        mock_get.return_value = mock_response

        with TMDBClient(api_key="invalid") as client:
            with pytest.raises(TMDBAuthError, match="Authentication failed"):
                client.get_movie(1)

    @patch("httpx.Client.get")
    def test_handle_404_error(self, mock_get: MagicMock) -> None:
        """Test handling of 404 not found error."""
        mock_response = MagicMock()
        mock_response.status_code = 404
        mock_get.return_value = mock_response

        with TMDBClient(api_key="test") as client:
            with pytest.raises(TMDBNotFoundError):
                client.get_movie(999999999)

    @patch("httpx.Client.get")
    def test_handle_429_rate_limit(self, mock_get: MagicMock) -> None:
        """Test handling of 429 rate limit error."""
        mock_response = MagicMock()
        mock_response.status_code = 429
        mock_response.headers = {"Retry-After": "10"}
        mock_get.return_value = mock_response

        with TMDBClient(api_key="test") as client:
            with pytest.raises(TMDBRateLimitError) as exc_info:
                client.get_movie(1)

        assert exc_info.value.retry_after == 10

    @patch("httpx.Client.get")
    def test_test_connection_success(self, mock_get: MagicMock) -> None:
        """Test successful connection test."""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"images": {}}
        mock_get.return_value = mock_response

        with TMDBClient(api_key="test") as client:
            assert client.test_connection() is True
