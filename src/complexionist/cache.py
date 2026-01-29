"""Single-file JSON caching for API responses.

Cache is stored in a single file: `complexionist.cache.json` next to the
config file or executable for maximum portability.

File structure:
    {
        "_meta": {
            "version": 1,
            "created_at": "2025-01-25T10:00:00Z"
        },
        "fingerprints": {
            "Movies": {
                "item_count": 542,
                "id_hash": "abc123...",
                "computed_at": "2025-01-25T10:00:00Z"
            }
        },
        "entries": {
            "tmdb/movies/12345": {
                "_cache_meta": {
                    "cached_at": "2025-01-25T10:00:00Z",
                    "expires_at": "2025-02-01T10:00:00Z",
                    "ttl_hours": 168
                },
                "data": { ... }
            },
            "tmdb/collections/67890": { ... },
            "tvdb/episodes/11111": { ... }
        }
    }
"""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass, field
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import TYPE_CHECKING, Any, cast

if TYPE_CHECKING:
    from complexionist.plex import PlexMovie, PlexShow

# Default TTLs in hours
TMDB_MOVIE_WITH_COLLECTION_TTL_HOURS = 720  # 30 days (collection membership rarely changes)
TMDB_MOVIE_WITHOUT_COLLECTION_TTL_HOURS = 168  # 7 days (might be added to a collection)
TMDB_COLLECTION_TTL_HOURS = 720  # 30 days (new movies picked up via movie lookup)
TVDB_SERIES_TTL_HOURS = 168  # 7 days (series info like poster rarely changes)
TVDB_EPISODES_TTL_HOURS = 24  # 24 hours

# Cache file version for future migrations
CACHE_VERSION = 1


@dataclass
class CacheStats:
    """Statistics about the cache."""

    total_entries: int
    total_size_bytes: int
    tmdb_movies: int
    tmdb_collections: int
    tvdb_episodes: int
    oldest_entry: datetime | None
    newest_entry: datetime | None

    @property
    def total_size_mb(self) -> float:
        """Total size in megabytes."""
        return self.total_size_bytes / (1024 * 1024)

    @property
    def total_size_kb(self) -> float:
        """Total size in kilobytes."""
        return self.total_size_bytes / 1024


def get_cache_file_path() -> Path:
    """Get the path to the cache file.

    Cache is stored next to the config file for portability.
    Falls back to exe directory if no config is loaded.

    Returns:
        Path to cache file (complexionist.cache.json).
    """
    from complexionist.config import get_config_path, get_exe_directory

    # Try to use config file location
    config_path = get_config_path()
    if config_path is not None:
        return config_path.parent / "complexionist.cache.json"

    # Fall back to exe directory
    return get_exe_directory() / "complexionist.cache.json"


# Keep old name for backwards compatibility with tests
def get_cache_dir() -> Path:
    """Get the cache directory (deprecated - returns parent of cache file)."""
    return get_cache_file_path().parent


@dataclass
class LibraryFingerprint:
    """Fingerprint of a Plex library for cache invalidation."""

    item_count: int
    id_hash: str
    computed_at: datetime = field(default_factory=lambda: datetime.now(UTC))

    def matches(self, other: LibraryFingerprint) -> bool:
        """Check if this fingerprint matches another."""
        return self.item_count == other.item_count and self.id_hash == other.id_hash

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for JSON serialization."""
        return {
            "item_count": self.item_count,
            "id_hash": self.id_hash,
            "computed_at": self.computed_at.isoformat(),
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> LibraryFingerprint:
        """Create from dictionary."""
        return cls(
            item_count=data["item_count"],
            id_hash=data["id_hash"],
            computed_at=datetime.fromisoformat(data["computed_at"]),
        )


def compute_fingerprint(
    items: list[PlexMovie] | list[PlexShow],
) -> LibraryFingerprint:
    """Compute a fingerprint for a list of Plex items.

    The fingerprint consists of:
    - Item count
    - MD5 hash of sorted rating keys

    Args:
        items: List of PlexMovie or PlexShow objects.

    Returns:
        LibraryFingerprint for the items.
    """
    # Sort by rating_key for consistent hashing
    rating_keys = sorted(str(item.rating_key) for item in items)
    id_string = ",".join(rating_keys)
    id_hash = hashlib.md5(id_string.encode()).hexdigest()

    return LibraryFingerprint(
        item_count=len(items),
        id_hash=id_hash,
    )


class Cache:
    """Single-file JSON cache for API responses.

    All cache entries are stored in a single JSON file for portability.
    The file is loaded on first access and saved periodically or on flush.

    To avoid file system contention (especially on Windows), saves are batched:
    - Changes are accumulated in memory
    - Auto-save triggers every `auto_save_threshold` changes
    - Call `flush()` at the end of operations to ensure all changes are saved
    """

    def __init__(
        self,
        cache_dir: Path | None = None,
        enabled: bool = True,
        auto_save_threshold: int = 250,
    ) -> None:
        """Initialize the cache.

        Args:
            cache_dir: Custom cache directory (file will be placed here).
                Defaults to same directory as config file.
            enabled: Whether caching is enabled. If False, all operations are no-ops.
            auto_save_threshold: Number of changes before auto-saving to disk.
                Set to 0 to disable auto-save (manual flush only). Default is 250.
        """
        self.enabled = enabled
        self.auto_save_threshold = auto_save_threshold
        if cache_dir is not None:
            self.cache_file = cache_dir / "complexionist.cache.json"
        else:
            self.cache_file = get_cache_file_path()
        self.cache_dir = self.cache_file.parent  # For backwards compatibility
        self._data: dict[str, Any] | None = None
        self._dirty_count: int = 0  # Track unsaved changes

    def _make_key(self, namespace: str, category: str, key: str) -> str:
        """Make a cache entry key from namespace/category/key."""
        return f"{namespace}/{category}/{key}"

    def _load(self) -> dict[str, Any]:
        """Load cache data from disk (lazy loading)."""
        if self._data is not None:
            return self._data

        if not self.cache_file.exists():
            self._data = self._empty_cache()
            return self._data

        try:
            with open(self.cache_file, encoding="utf-8") as f:
                self._data = json.load(f)
                # Ensure required keys exist
                if "entries" not in self._data:
                    self._data["entries"] = {}
                if "fingerprints" not in self._data:
                    self._data["fingerprints"] = {}
                return self._data
        except (json.JSONDecodeError, OSError):
            # Corrupted file - start fresh
            self._data = self._empty_cache()
            return self._data

    def _empty_cache(self) -> dict[str, Any]:
        """Create an empty cache structure."""
        return {
            "_meta": {
                "version": CACHE_VERSION,
                "created_at": datetime.now(UTC).isoformat(),
            },
            "fingerprints": {},
            "entries": {},
        }

    def _save(self) -> None:
        """Save cache data to disk (unconditionally).

        Writes directly to the cache file to minimize SSD wear and avoid
        temp file permission issues on Windows. Since writes are batched,
        the risk of corruption from interrupted writes is minimal.
        """
        if self._data is None:
            return

        # Ensure parent directory exists
        self.cache_file.parent.mkdir(parents=True, exist_ok=True)

        # Write directly to cache file (no temp file swap)
        with open(self.cache_file, "w", encoding="utf-8") as f:
            json.dump(self._data, f, indent=2, default=str)

        self._dirty_count = 0  # Reset after successful save

    def _mark_dirty(self) -> None:
        """Mark the cache as having unsaved changes and maybe auto-save."""
        self._dirty_count += 1
        if self.auto_save_threshold > 0 and self._dirty_count >= self.auto_save_threshold:
            self._save()

    def flush(self) -> None:
        """Flush any pending changes to disk.

        Call this at the end of operations to ensure all cached data is persisted.
        Safe to call even if there are no pending changes.
        """
        if self._dirty_count > 0:
            self._save()

    @property
    def pending_changes(self) -> int:
        """Number of changes pending save."""
        return self._dirty_count

    def get(self, namespace: str, category: str, key: str) -> dict[str, Any] | None:
        """Get a cached entry if it exists and hasn't expired.

        Args:
            namespace: Top-level namespace (e.g., "tmdb", "tvdb").
            category: Category within namespace (e.g., "movies", "collections").
            key: Unique key for the entry.

        Returns:
            Cached data dict if found and valid, None otherwise.
        """
        if not self.enabled:
            return None

        data = self._load()
        cache_key = self._make_key(namespace, category, key)
        entry = data["entries"].get(cache_key)

        if entry is None:
            return None

        # Check expiration
        meta = entry.get("_cache_meta", {})
        expires_at_str = meta.get("expires_at")

        if expires_at_str:
            try:
                expires_at = datetime.fromisoformat(expires_at_str)
                if datetime.now(UTC) > expires_at:
                    # Expired - remove and return None
                    del data["entries"][cache_key]
                    self._mark_dirty()
                    return None
            except ValueError:
                # Invalid date - remove entry
                del data["entries"][cache_key]
                self._mark_dirty()
                return None

        return cast(dict[str, Any] | None, entry.get("data"))

    def set(
        self,
        namespace: str,
        category: str,
        key: str,
        data: dict[str, Any],
        ttl_hours: int,
        description: str = "",
    ) -> None:
        """Store data in the cache.

        Args:
            namespace: Top-level namespace (e.g., "tmdb", "tvdb").
            category: Category within namespace (e.g., "movies", "collections").
            key: Unique key for the entry.
            data: Data to cache.
            ttl_hours: Time-to-live in hours.
            description: Human-readable description (not stored in single-file mode).
        """
        if not self.enabled:
            return

        cache_data = self._load()
        cache_key = self._make_key(namespace, category, key)

        now = datetime.now(UTC)
        expires_at = now + timedelta(hours=ttl_hours)

        cache_data["entries"][cache_key] = {
            "_cache_meta": {
                "cached_at": now.isoformat(),
                "expires_at": expires_at.isoformat(),
                "ttl_hours": ttl_hours,
            },
            "data": data,
        }

        self._mark_dirty()

    def delete(self, namespace: str, category: str, key: str) -> bool:
        """Delete a specific cache entry.

        Args:
            namespace: Top-level namespace.
            category: Category within namespace.
            key: Unique key for the entry.

        Returns:
            True if entry was deleted, False if it didn't exist.
        """
        data = self._load()
        cache_key = self._make_key(namespace, category, key)

        if cache_key in data["entries"]:
            del data["entries"][cache_key]
            self._mark_dirty()
            return True
        return False

    def clear(self, namespace: str | None = None) -> int:
        """Clear cache entries.

        Args:
            namespace: If provided, only clear entries in this namespace.
                If None, clear all entries.

        Returns:
            Number of entries deleted.
        """
        data = self._load()
        count = 0

        if namespace:
            # Clear specific namespace
            prefix = f"{namespace}/"
            keys_to_delete = [k for k in data["entries"] if k.startswith(prefix)]
            for key in keys_to_delete:
                del data["entries"][key]
                count += 1
        else:
            # Clear all
            count = len(data["entries"])
            data["entries"] = {}

        if count > 0:
            self._save()

        return count

    def stats(self) -> CacheStats:
        """Get cache statistics.

        Returns:
            CacheStats with counts and size information.
        """
        data = self._load()
        entries = data.get("entries", {})

        tmdb_movies = 0
        tmdb_collections = 0
        tvdb_episodes = 0
        oldest: datetime | None = None
        newest: datetime | None = None

        for cache_key, entry in entries.items():
            # Count by category
            parts = cache_key.split("/")
            if len(parts) >= 2:
                namespace, category = parts[0], parts[1]
                if namespace == "tmdb":
                    if category == "movies":
                        tmdb_movies += 1
                    elif category == "collections":
                        tmdb_collections += 1
                elif namespace == "tvdb":
                    if category == "episodes":
                        tvdb_episodes += 1

            # Track oldest/newest
            cached_at_str = entry.get("_cache_meta", {}).get("cached_at")
            if cached_at_str:
                try:
                    cached_at = datetime.fromisoformat(cached_at_str)
                    if oldest is None or cached_at < oldest:
                        oldest = cached_at
                    if newest is None or cached_at > newest:
                        newest = cached_at
                except ValueError:
                    continue

        # Get file size
        total_size = 0
        if self.cache_file.exists():
            total_size = self.cache_file.stat().st_size

        return CacheStats(
            total_entries=len(entries),
            total_size_bytes=total_size,
            tmdb_movies=tmdb_movies,
            tmdb_collections=tmdb_collections,
            tvdb_episodes=tvdb_episodes,
            oldest_entry=oldest,
            newest_entry=newest,
        )

    def get_expired_count(self) -> int:
        """Count expired entries that haven't been cleaned up yet.

        Returns:
            Number of expired entries.
        """
        data = self._load()
        count = 0
        now = datetime.now(UTC)

        for entry in data.get("entries", {}).values():
            expires_at_str = entry.get("_cache_meta", {}).get("expires_at")
            if expires_at_str:
                try:
                    expires_at = datetime.fromisoformat(expires_at_str)
                    if now > expires_at:
                        count += 1
                except ValueError:
                    count += 1  # Invalid date counts as expired

        return count

    def cleanup_expired(self) -> int:
        """Remove all expired entries.

        Returns:
            Number of entries removed.
        """
        data = self._load()
        now = datetime.now(UTC)
        keys_to_delete = []

        for cache_key, entry in data.get("entries", {}).items():
            expires_at_str = entry.get("_cache_meta", {}).get("expires_at")
            if expires_at_str:
                try:
                    expires_at = datetime.fromisoformat(expires_at_str)
                    if now > expires_at:
                        keys_to_delete.append(cache_key)
                except ValueError:
                    keys_to_delete.append(cache_key)

        for key in keys_to_delete:
            del data["entries"][key]

        if keys_to_delete:
            self._save()

        return len(keys_to_delete)

    # =========================================================================
    # Fingerprint Management
    # =========================================================================

    def get_library_fingerprint(self, library_name: str) -> LibraryFingerprint | None:
        """Get the stored fingerprint for a library.

        Args:
            library_name: Name of the Plex library.

        Returns:
            Stored fingerprint, or None if not found.
        """
        data = self._load()
        lib_data = data.get("fingerprints", {}).get(library_name)
        if lib_data:
            return LibraryFingerprint.from_dict(lib_data)
        return None

    def set_library_fingerprint(self, library_name: str, fingerprint: LibraryFingerprint) -> None:
        """Store the fingerprint for a library.

        Args:
            library_name: Name of the Plex library.
            fingerprint: Fingerprint to store.
        """
        data = self._load()
        data["fingerprints"][library_name] = fingerprint.to_dict()
        self._mark_dirty()

    def check_fingerprint(self, library_name: str, current_fingerprint: LibraryFingerprint) -> bool:
        """Check if the library fingerprint matches the stored one.

        Args:
            library_name: Name of the Plex library.
            current_fingerprint: Current fingerprint computed from library items.

        Returns:
            True if fingerprints match (cache is valid), False otherwise.
        """
        stored = self.get_library_fingerprint(library_name)
        if stored is None:
            return False
        return stored.matches(current_fingerprint)

    def invalidate_library(self, library_name: str) -> int:
        """Invalidate the cache for a specific library.

        Removes the stored fingerprint and clears related cache entries.

        Args:
            library_name: Name of the library to invalidate.

        Returns:
            Number of cache entries cleared.
        """
        data = self._load()

        # Remove fingerprint
        if library_name in data.get("fingerprints", {}):
            del data["fingerprints"][library_name]

        # Clear all entries (could be more selective in future)
        count = len(data.get("entries", {}))
        data["entries"] = {}

        self._save()
        return count

    def refresh(self) -> int:
        """Force refresh - clear all cache and fingerprints.

        Returns:
            Number of cache entries cleared.
        """
        data = self._load()
        count = len(data.get("entries", {}))

        # Reset to empty
        self._data = self._empty_cache()
        self._save()

        return count
