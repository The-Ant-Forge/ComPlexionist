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
    get_cache_dir,
)


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
        """Test get_cache_dir returns correct path."""
        cache_dir = get_cache_dir()
        assert cache_dir == Path.home() / ".complexionist" / "cache"


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

            # Create an already-expired entry manually
            path = Path(tmpdir) / "tmdb" / "movies" / "123.json"
            path.parent.mkdir(parents=True, exist_ok=True)

            past_time = datetime.now(UTC) - timedelta(hours=1)
            entry = {
                "_cache_meta": {
                    "cached_at": past_time.isoformat(),
                    "expires_at": past_time.isoformat(),  # Already expired
                    "ttl_hours": 1,
                },
                "data": {"id": 123},
            }
            with open(path, "w", encoding="utf-8") as f:
                json.dump(entry, f)

            # Should return None and delete the file
            result = cache.get("tmdb", "movies", "123")
            assert result is None
            assert not path.exists()

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

            # No file should be created
            path = Path(tmpdir) / "tmdb" / "movies" / "123.json"
            assert not path.exists()

    def test_cache_file_structure(self) -> None:
        """Test cache file has correct structure."""
        with tempfile.TemporaryDirectory() as tmpdir:
            cache = Cache(cache_dir=Path(tmpdir))

            data = {"id": 123, "title": "Test Movie", "year": 2020}
            cache.set("tmdb", "movies", "123", data, ttl_hours=168, description="Test Movie (2020)")

            # Read the raw file
            path = Path(tmpdir) / "tmdb" / "movies" / "123.json"
            with open(path, encoding="utf-8") as f:
                entry = json.load(f)

            # Check structure
            assert "_cache_meta" in entry
            assert "data" in entry
            assert entry["_cache_meta"]["ttl_hours"] == 168
            assert entry["_cache_meta"]["description"] == "Test Movie (2020)"
            assert "cached_at" in entry["_cache_meta"]
            assert "expires_at" in entry["_cache_meta"]
            assert entry["data"] == data

    def test_corrupted_cache_file(self) -> None:
        """Test corrupted cache file is handled gracefully."""
        with tempfile.TemporaryDirectory() as tmpdir:
            cache = Cache(cache_dir=Path(tmpdir))

            # Create a corrupted file
            path = Path(tmpdir) / "tmdb" / "movies" / "123.json"
            path.parent.mkdir(parents=True, exist_ok=True)
            with open(path, "w", encoding="utf-8") as f:
                f.write("not valid json{")

            # Should return None and delete the file
            result = cache.get("tmdb", "movies", "123")
            assert result is None
            assert not path.exists()


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

            # Create an expired entry manually
            path = Path(tmpdir) / "tmdb" / "movies" / "123.json"
            path.parent.mkdir(parents=True, exist_ok=True)

            past_time = datetime.now(UTC) - timedelta(hours=1)
            entry = {
                "_cache_meta": {
                    "cached_at": past_time.isoformat(),
                    "expires_at": past_time.isoformat(),
                    "ttl_hours": 1,
                },
                "data": {"id": 123},
            }
            with open(path, "w", encoding="utf-8") as f:
                json.dump(entry, f)

            # Add a non-expired entry
            cache.set("tmdb", "movies", "456", {"id": 456}, ttl_hours=24)

            count = cache.get_expired_count()
            assert count == 1

    def test_cleanup_expired(self) -> None:
        """Test cleaning up expired entries."""
        with tempfile.TemporaryDirectory() as tmpdir:
            cache = Cache(cache_dir=Path(tmpdir))

            # Create an expired entry manually
            path = Path(tmpdir) / "tmdb" / "movies" / "123.json"
            path.parent.mkdir(parents=True, exist_ok=True)

            past_time = datetime.now(UTC) - timedelta(hours=1)
            entry = {
                "_cache_meta": {
                    "cached_at": past_time.isoformat(),
                    "expires_at": past_time.isoformat(),
                    "ttl_hours": 1,
                },
                "data": {"id": 123},
            }
            with open(path, "w", encoding="utf-8") as f:
                json.dump(entry, f)

            # Add a non-expired entry
            cache.set("tmdb", "movies", "456", {"id": 456}, ttl_hours=24)

            # Cleanup should remove 1 expired entry
            count = cache.cleanup_expired()
            assert count == 1

            # Expired entry should be gone
            assert not path.exists()

            # Non-expired entry should remain
            assert cache.get("tmdb", "movies", "456") is not None
