"""Tests for the caching module."""

import json
import tempfile
from datetime import UTC, datetime, timedelta
from pathlib import Path

from complexionist.cache import (
    TMDB_COLLECTION_TTL_HOURS,
    TMDB_MOVIE_TTL_HOURS,
    TVDB_EPISODES_TTL_HOURS,
    Cache,
    CacheStats,
    LibraryFingerprint,
    compute_fingerprint,
    get_cache_dir,
)
from complexionist.plex import PlexMovie


class TestCacheDefaults:
    """Tests for cache module constants and defaults."""

    def test_tmdb_movie_ttl(self) -> None:
        """Test TMDB movie TTL is 7 days."""
        assert TMDB_MOVIE_TTL_HOURS == 168

    def test_tmdb_collection_ttl(self) -> None:
        """Test TMDB collection TTL is 7 days."""
        assert TMDB_COLLECTION_TTL_HOURS == 168

    def test_tvdb_episodes_ttl(self) -> None:
        """Test TVDB episodes TTL is 24 hours."""
        assert TVDB_EPISODES_TTL_HOURS == 24

    def test_get_cache_dir(self) -> None:
        """Test get_cache_dir returns a valid directory.

        Cache is now stored in a single file next to config or exe,
        and get_cache_dir returns the parent directory.
        """
        cache_dir = get_cache_dir()
        # Should return a valid parent directory
        assert cache_dir.exists() or cache_dir.parent.exists()


class TestCacheStats:
    """Tests for CacheStats dataclass."""

    def test_total_size_mb(self) -> None:
        """Test total_size_mb conversion."""
        stats = CacheStats(
            total_entries=10,
            total_size_bytes=2 * 1024 * 1024,  # 2 MB
            tmdb_movies=5,
            tmdb_collections=3,
            tvdb_episodes=2,
            oldest_entry=None,
            newest_entry=None,
        )
        assert stats.total_size_mb == 2.0

    def test_total_size_kb(self) -> None:
        """Test total_size_kb conversion."""
        stats = CacheStats(
            total_entries=10,
            total_size_bytes=10 * 1024,  # 10 KB
            tmdb_movies=5,
            tmdb_collections=3,
            tvdb_episodes=2,
            oldest_entry=None,
            newest_entry=None,
        )
        assert stats.total_size_kb == 10.0


class TestCacheInit:
    """Tests for Cache initialization."""

    def test_init_default_cache_dir(self) -> None:
        """Test cache uses default directory."""
        cache = Cache()
        assert cache.cache_dir == get_cache_dir()
        assert cache.enabled is True

    def test_init_custom_cache_dir(self) -> None:
        """Test cache uses custom directory."""
        custom_dir = Path("/custom/cache")
        cache = Cache(cache_dir=custom_dir)
        assert cache.cache_dir == custom_dir

    def test_init_disabled(self) -> None:
        """Test cache can be disabled."""
        cache = Cache(enabled=False)
        assert cache.enabled is False


class TestCacheGetSet:
    """Tests for Cache get/set operations."""

    def test_set_and_get(self) -> None:
        """Test basic set and get."""
        with tempfile.TemporaryDirectory() as tmpdir:
            cache = Cache(cache_dir=Path(tmpdir))

            data = {"id": 123, "title": "Test Movie"}
            cache.set("tmdb", "movies", "123", data, ttl_hours=24, description="Test Movie")

            result = cache.get("tmdb", "movies", "123")
            assert result == data

    def test_get_nonexistent(self) -> None:
        """Test get returns None for nonexistent entry."""
        with tempfile.TemporaryDirectory() as tmpdir:
            cache = Cache(cache_dir=Path(tmpdir))
            result = cache.get("tmdb", "movies", "999")
            assert result is None

    def test_get_expired(self) -> None:
        """Test get returns None for expired entry."""
        with tempfile.TemporaryDirectory() as tmpdir:
            cache = Cache(cache_dir=Path(tmpdir))

            # Create an already-expired entry in the single cache file
            cache_file = Path(tmpdir) / "complexionist.cache.json"
            past_time = datetime.now(UTC) - timedelta(hours=1)
            cache_data = {
                "_meta": {"version": 1, "created_at": past_time.isoformat()},
                "fingerprints": {},
                "entries": {
                    "tmdb/movies/123": {
                        "_cache_meta": {
                            "cached_at": past_time.isoformat(),
                            "expires_at": past_time.isoformat(),  # Already expired
                            "ttl_hours": 1,
                        },
                        "data": {"id": 123},
                    }
                },
            }
            with open(cache_file, "w", encoding="utf-8") as f:
                json.dump(cache_data, f)

            # Should return None for expired entry
            result = cache.get("tmdb", "movies", "123")
            assert result is None

    def test_get_when_disabled(self) -> None:
        """Test get returns None when cache is disabled."""
        with tempfile.TemporaryDirectory() as tmpdir:
            cache = Cache(cache_dir=Path(tmpdir), enabled=False)

            # Set should be a no-op
            cache.set("tmdb", "movies", "123", {"id": 123}, ttl_hours=24)

            # Get should return None
            result = cache.get("tmdb", "movies", "123")
            assert result is None

    def test_set_when_disabled(self) -> None:
        """Test set is no-op when cache is disabled."""
        with tempfile.TemporaryDirectory() as tmpdir:
            cache = Cache(cache_dir=Path(tmpdir), enabled=False)
            cache.set("tmdb", "movies", "123", {"id": 123}, ttl_hours=24)

            # Cache file should not be created
            cache_file = Path(tmpdir) / "complexionist.cache.json"
            assert not cache_file.exists()

    def test_cache_file_structure(self) -> None:
        """Test cache file has correct structure."""
        with tempfile.TemporaryDirectory() as tmpdir:
            cache = Cache(cache_dir=Path(tmpdir))

            data = {"id": 123, "title": "Test Movie", "year": 2020}
            cache.set("tmdb", "movies", "123", data, ttl_hours=168, description="Test Movie (2020)")
            cache.flush()  # Force write to disk

            # Read the raw file
            cache_file = Path(tmpdir) / "complexionist.cache.json"
            with open(cache_file, encoding="utf-8") as f:
                cache_data = json.load(f)

            # Check structure
            assert "_meta" in cache_data
            assert "fingerprints" in cache_data
            assert "entries" in cache_data
            assert "tmdb/movies/123" in cache_data["entries"]

            entry = cache_data["entries"]["tmdb/movies/123"]
            assert "_cache_meta" in entry
            assert "data" in entry
            assert entry["_cache_meta"]["ttl_hours"] == 168
            assert "cached_at" in entry["_cache_meta"]
            assert "expires_at" in entry["_cache_meta"]
            assert entry["data"] == data

    def test_corrupted_cache_file(self) -> None:
        """Test corrupted cache file is handled gracefully."""
        with tempfile.TemporaryDirectory() as tmpdir:
            cache = Cache(cache_dir=Path(tmpdir))

            # Create a corrupted file
            cache_file = Path(tmpdir) / "complexionist.cache.json"
            with open(cache_file, "w", encoding="utf-8") as f:
                f.write("not valid json{")

            # Should return None and create fresh cache
            result = cache.get("tmdb", "movies", "123")
            assert result is None

            # Should be able to set new data
            cache.set("tmdb", "movies", "123", {"id": 123}, ttl_hours=24)
            assert cache.get("tmdb", "movies", "123") == {"id": 123}


class TestCacheDelete:
    """Tests for Cache delete operation."""

    def test_delete_existing(self) -> None:
        """Test deleting an existing entry."""
        with tempfile.TemporaryDirectory() as tmpdir:
            cache = Cache(cache_dir=Path(tmpdir))

            cache.set("tmdb", "movies", "123", {"id": 123}, ttl_hours=24)
            assert cache.get("tmdb", "movies", "123") is not None

            result = cache.delete("tmdb", "movies", "123")
            assert result is True
            assert cache.get("tmdb", "movies", "123") is None

    def test_delete_nonexistent(self) -> None:
        """Test deleting a nonexistent entry returns False."""
        with tempfile.TemporaryDirectory() as tmpdir:
            cache = Cache(cache_dir=Path(tmpdir))
            result = cache.delete("tmdb", "movies", "999")
            assert result is False


class TestCacheClear:
    """Tests for Cache clear operation."""

    def test_clear_all(self) -> None:
        """Test clearing all cache entries."""
        with tempfile.TemporaryDirectory() as tmpdir:
            cache = Cache(cache_dir=Path(tmpdir))

            # Add entries to multiple namespaces
            cache.set("tmdb", "movies", "1", {"id": 1}, ttl_hours=24)
            cache.set("tmdb", "collections", "2", {"id": 2}, ttl_hours=24)
            cache.set("tvdb", "episodes", "3", {"id": 3}, ttl_hours=24)

            count = cache.clear()
            assert count == 3

            # All entries should be gone
            assert cache.get("tmdb", "movies", "1") is None
            assert cache.get("tmdb", "collections", "2") is None
            assert cache.get("tvdb", "episodes", "3") is None

    def test_clear_namespace(self) -> None:
        """Test clearing only a specific namespace."""
        with tempfile.TemporaryDirectory() as tmpdir:
            cache = Cache(cache_dir=Path(tmpdir))

            cache.set("tmdb", "movies", "1", {"id": 1}, ttl_hours=24)
            cache.set("tvdb", "episodes", "2", {"id": 2}, ttl_hours=24)

            count = cache.clear(namespace="tmdb")
            assert count == 1

            # TMDB entry should be gone, TVDB should remain
            assert cache.get("tmdb", "movies", "1") is None
            assert cache.get("tvdb", "episodes", "2") is not None

    def test_clear_empty_cache(self) -> None:
        """Test clearing empty cache returns 0."""
        with tempfile.TemporaryDirectory() as tmpdir:
            cache = Cache(cache_dir=Path(tmpdir))
            count = cache.clear()
            assert count == 0


class TestCacheStatsOperation:
    """Tests for Cache stats operation."""

    def test_stats_empty_cache(self) -> None:
        """Test stats for empty cache."""
        with tempfile.TemporaryDirectory() as tmpdir:
            cache = Cache(cache_dir=Path(tmpdir))
            stats = cache.stats()

            assert stats.total_entries == 0
            assert stats.total_size_bytes == 0
            assert stats.tmdb_movies == 0
            assert stats.tmdb_collections == 0
            assert stats.tvdb_episodes == 0
            assert stats.oldest_entry is None
            assert stats.newest_entry is None

    def test_stats_with_entries(self) -> None:
        """Test stats with cache entries."""
        with tempfile.TemporaryDirectory() as tmpdir:
            cache = Cache(cache_dir=Path(tmpdir))

            cache.set("tmdb", "movies", "1", {"id": 1}, ttl_hours=24)
            cache.set("tmdb", "movies", "2", {"id": 2}, ttl_hours=24)
            cache.set("tmdb", "collections", "3", {"id": 3}, ttl_hours=24)
            cache.set("tvdb", "episodes", "4", {"id": 4}, ttl_hours=24)
            cache.flush()  # Force write to disk for file size check

            stats = cache.stats()

            assert stats.total_entries == 4
            assert stats.total_size_bytes > 0
            assert stats.tmdb_movies == 2
            assert stats.tmdb_collections == 1
            assert stats.tvdb_episodes == 1
            assert stats.oldest_entry is not None
            assert stats.newest_entry is not None


class TestCacheExpiration:
    """Tests for cache expiration handling."""

    def test_get_expired_count(self) -> None:
        """Test counting expired entries."""
        with tempfile.TemporaryDirectory() as tmpdir:
            cache = Cache(cache_dir=Path(tmpdir))

            # Create cache with an expired entry
            cache_file = Path(tmpdir) / "complexionist.cache.json"
            past_time = datetime.now(UTC) - timedelta(hours=1)
            future_time = datetime.now(UTC) + timedelta(hours=24)
            cache_data = {
                "_meta": {"version": 1, "created_at": datetime.now(UTC).isoformat()},
                "fingerprints": {},
                "entries": {
                    "tmdb/movies/123": {
                        "_cache_meta": {
                            "cached_at": past_time.isoformat(),
                            "expires_at": past_time.isoformat(),
                            "ttl_hours": 1,
                        },
                        "data": {"id": 123},
                    },
                    "tmdb/movies/456": {
                        "_cache_meta": {
                            "cached_at": datetime.now(UTC).isoformat(),
                            "expires_at": future_time.isoformat(),
                            "ttl_hours": 24,
                        },
                        "data": {"id": 456},
                    },
                },
            }
            with open(cache_file, "w", encoding="utf-8") as f:
                json.dump(cache_data, f)

            # Force reload
            cache._data = None

            count = cache.get_expired_count()
            assert count == 1

    def test_cleanup_expired(self) -> None:
        """Test cleaning up expired entries."""
        with tempfile.TemporaryDirectory() as tmpdir:
            cache = Cache(cache_dir=Path(tmpdir))

            # Create cache with an expired entry
            cache_file = Path(tmpdir) / "complexionist.cache.json"
            past_time = datetime.now(UTC) - timedelta(hours=1)
            future_time = datetime.now(UTC) + timedelta(hours=24)
            cache_data = {
                "_meta": {"version": 1, "created_at": datetime.now(UTC).isoformat()},
                "fingerprints": {},
                "entries": {
                    "tmdb/movies/123": {
                        "_cache_meta": {
                            "cached_at": past_time.isoformat(),
                            "expires_at": past_time.isoformat(),
                            "ttl_hours": 1,
                        },
                        "data": {"id": 123},
                    },
                    "tmdb/movies/456": {
                        "_cache_meta": {
                            "cached_at": datetime.now(UTC).isoformat(),
                            "expires_at": future_time.isoformat(),
                            "ttl_hours": 24,
                        },
                        "data": {"id": 456},
                    },
                },
            }
            with open(cache_file, "w", encoding="utf-8") as f:
                json.dump(cache_data, f)

            # Force reload
            cache._data = None

            # Cleanup should remove 1 expired entry
            count = cache.cleanup_expired()
            assert count == 1

            # Non-expired entry should remain
            assert cache.get("tmdb", "movies", "456") is not None

            # Expired entry should be gone
            assert cache.get("tmdb", "movies", "123") is None


class TestLibraryFingerprint:
    """Tests for library fingerprinting."""

    def test_compute_fingerprint(self) -> None:
        """Test computing fingerprint from movie list."""
        movies = [
            PlexMovie(rating_key="100", title="Movie A"),
            PlexMovie(rating_key="200", title="Movie B"),
            PlexMovie(rating_key="300", title="Movie C"),
        ]

        fingerprint = compute_fingerprint(movies)

        assert fingerprint.item_count == 3
        assert len(fingerprint.id_hash) == 32  # MD5 hash length

    def test_fingerprint_order_independent(self) -> None:
        """Test that fingerprint is independent of item order."""
        movies1 = [
            PlexMovie(rating_key="100", title="Movie A"),
            PlexMovie(rating_key="200", title="Movie B"),
        ]
        movies2 = [
            PlexMovie(rating_key="200", title="Movie B"),
            PlexMovie(rating_key="100", title="Movie A"),
        ]

        fp1 = compute_fingerprint(movies1)
        fp2 = compute_fingerprint(movies2)

        # Same items in different order should produce same fingerprint
        assert fp1.matches(fp2)

    def test_fingerprint_changes_with_new_item(self) -> None:
        """Test that fingerprint changes when item is added."""
        movies1 = [
            PlexMovie(rating_key="100", title="Movie A"),
        ]
        movies2 = [
            PlexMovie(rating_key="100", title="Movie A"),
            PlexMovie(rating_key="200", title="Movie B"),
        ]

        fp1 = compute_fingerprint(movies1)
        fp2 = compute_fingerprint(movies2)

        # Different items should produce different fingerprints
        assert not fp1.matches(fp2)

    def test_fingerprint_serialization(self) -> None:
        """Test fingerprint to_dict and from_dict."""
        movies = [PlexMovie(rating_key="100", title="Movie A")]
        fingerprint = compute_fingerprint(movies)

        data = fingerprint.to_dict()
        restored = LibraryFingerprint.from_dict(data)

        assert restored.item_count == fingerprint.item_count
        assert restored.id_hash == fingerprint.id_hash


class TestCacheFingerprints:
    """Tests for cache fingerprint management."""

    def test_set_and_get_library_fingerprint(self) -> None:
        """Test storing and retrieving library fingerprints."""
        with tempfile.TemporaryDirectory() as tmpdir:
            cache = Cache(cache_dir=Path(tmpdir))

            movies = [
                PlexMovie(rating_key="100", title="Movie A"),
                PlexMovie(rating_key="200", title="Movie B"),
            ]
            fingerprint = compute_fingerprint(movies)

            cache.set_library_fingerprint("Movies", fingerprint)
            retrieved = cache.get_library_fingerprint("Movies")

            assert retrieved is not None
            assert retrieved.item_count == fingerprint.item_count
            assert retrieved.id_hash == fingerprint.id_hash

    def test_get_nonexistent_fingerprint(self) -> None:
        """Test retrieving fingerprint for library that doesn't exist."""
        with tempfile.TemporaryDirectory() as tmpdir:
            cache = Cache(cache_dir=Path(tmpdir))

            result = cache.get_library_fingerprint("NonexistentLibrary")
            assert result is None

    def test_check_fingerprint_matches(self) -> None:
        """Test checking if fingerprint matches."""
        with tempfile.TemporaryDirectory() as tmpdir:
            cache = Cache(cache_dir=Path(tmpdir))

            movies = [PlexMovie(rating_key="100", title="Movie A")]
            fingerprint = compute_fingerprint(movies)

            cache.set_library_fingerprint("Movies", fingerprint)

            # Same fingerprint should match
            assert cache.check_fingerprint("Movies", fingerprint)

    def test_check_fingerprint_no_match(self) -> None:
        """Test checking when fingerprint doesn't match."""
        with tempfile.TemporaryDirectory() as tmpdir:
            cache = Cache(cache_dir=Path(tmpdir))

            movies1 = [PlexMovie(rating_key="100", title="Movie A")]
            movies2 = [
                PlexMovie(rating_key="100", title="Movie A"),
                PlexMovie(rating_key="200", title="Movie B"),
            ]

            fp1 = compute_fingerprint(movies1)
            fp2 = compute_fingerprint(movies2)

            cache.set_library_fingerprint("Movies", fp1)

            # Different fingerprint should not match
            assert not cache.check_fingerprint("Movies", fp2)

    def test_refresh_clears_fingerprints(self) -> None:
        """Test that refresh clears fingerprints."""
        with tempfile.TemporaryDirectory() as tmpdir:
            cache = Cache(cache_dir=Path(tmpdir))

            movies = [PlexMovie(rating_key="100", title="Movie A")]
            fingerprint = compute_fingerprint(movies)
            cache.set_library_fingerprint("Movies", fingerprint)

            # Add some cache data
            cache.set("tmdb", "movies", "100", {"id": 100}, ttl_hours=24)

            cache.refresh()

            # Fingerprint should be gone
            assert cache.get_library_fingerprint("Movies") is None

            # Cache should be empty
            assert cache.stats().total_entries == 0
