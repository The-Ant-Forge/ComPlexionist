# Code Review 1 — ComPlexionist

**Date:** 2026-02-10
**Scope:** Full codebase review covering code reuse, stability, security, efficiency, modern patterns, boot time, and dependencies.
**Approach:** Automated deep-dive with manual verification. Findings ordered by impact.

---

## Critical / High Impact

### 1. Non-Thread-Safe Cache Access

**File:** `src/complexionist/cache.py`
**Risk:** Data corruption / race conditions

The `Cache` class uses a shared `dict` (`self._data`) with no locking primitives — no `threading.Lock`, `RLock`, or any synchronization. The auto-save mechanism (`_mark_dirty` → `_save`) and lazy-load (`_load`) are both unprotected.

Currently the app is single-threaded for scanning, so this hasn't caused issues. However, Flet runs UI on a separate thread, and any future parallelization of scanning would immediately expose this.

**Suggestion:** Add a `threading.RLock` around `_load`, `_save`, `get`, `set`, `delete`, and `clear`. Minimal change — wrap the four public methods.

```python
import threading

class Cache:
    def __init__(self, ...):
        self._lock = threading.RLock()
        ...

    def get(self, *key_parts):
        with self._lock:
            ...

    def set(self, *key_parts, value, ttl_hours):
        with self._lock:
            ...
```

**Impact:** Prevents a class of hard-to-diagnose bugs if concurrency is ever introduced.

---

### 2. YAML Config Loading Has No Error Handling

**File:** `src/complexionist/config.py` — `_load_yaml_config()`
**Risk:** Crash on malformed config

```python
def _load_yaml_config(path: Path) -> dict[str, Any]:
    with open(path, encoding="utf-8") as f:
        return yaml.safe_load(f) or {}
```

No `try/except` for `yaml.YAMLError`, `OSError`, or `UnicodeDecodeError`. A single misplaced character in the YAML file crashes the app with an unhandled exception. By contrast, the INI loader is properly defensive with fallbacks.

**Suggestion:** Wrap in try/except, log the error, and either return empty config or show a user-friendly error message.

```python
def _load_yaml_config(path: Path) -> dict[str, Any]:
    try:
        with open(path, encoding="utf-8") as f:
            return yaml.safe_load(f) or {}
    except (yaml.YAMLError, OSError) as e:
        logger.error("Failed to load config from %s: %s", path, e)
        return {}
```

**Impact:** Prevents crash-on-startup for users who hand-edit their config.

---

### 3. Path Traversal Risk in `map_plex_path()`

**File:** `src/complexionist/config.py`
**Risk:** Low (consumer app, user-controlled config) but worth noting

`map_plex_path()` performs string prefix replacement to map Plex server paths to local/network paths. It does no validation that the result stays within expected boundaries. A malicious config entry could map paths to arbitrary filesystem locations.

**Suggestion:** Since this is a consumer desktop app where the user controls the config, this is informational. If the app is ever exposed to untrusted config input, add `Path.resolve()` validation and ensure mapped paths stay under expected roots.

**Impact:** Low for current use case. Note for future reference.

---

## Medium Impact

### 4. Results Screen Is 1,452 Lines with ~50% Movie/TV Duplication

**File:** `src/complexionist/gui/screens/results.py`
**Risk:** Maintenance burden, divergent bugs

The screen has near-identical parallel implementations:

| Movie | TV | Lines |
|-------|----|-------|
| `_build_movie_items()` | `_build_tv_items()` | ~270 / ~335 |
| `_create_movie_results()` | `_create_tv_results()` | ~95 / ~95 |
| `_ignore_collection()` | `_ignore_show()` | ~50 / ~45 |

Both follow the same pattern: build summary card → iterate items → create ExpansionTile → add action buttons → handle ignore. The TV version is slightly more complex (seasons inside shows) but the scaffolding is identical.

**Suggestion:** Extract a shared `_build_result_item()` builder that accepts a config object describing the differences (title field, subtitle format, ignore callback, nested items). This could cut 300-400 lines and ensure bug fixes apply to both paths.

**Impact:** Reduces maintenance burden and prevents "fixed for movies but not TV" bugs.

---

### 5. API Client Duplication (~60% Shared Boilerplate)

**Files:** `src/complexionist/tvdb/client.py` (438 lines), `src/complexionist/tmdb/client.py` (320 lines)
**Risk:** Maintenance burden

Both clients share nearly identical patterns:

- Error class hierarchy (3 error classes each, same structure)
- Constructor (api_key, timeout, httpx.Client, cache)
- Context manager (`__enter__`/`__exit__`)
- Response handler (`_handle_response` — status code → exception mapping)
- Cache check/set pattern (same TTL logic)
- `test_connection()` method

**Suggestion:** Extract a `BaseAPIClient` class with the shared machinery:

```python
class BaseAPIClient:
    def __init__(self, base_url, api_key, timeout, cache):
        ...
    def _handle_response(self, resp): ...
    def _cache_get(self, *key_parts): ...
    def _cache_set(self, *key_parts, value, ttl_hours): ...
    def __enter__(self): ...
    def __exit__(self): ...
```

Then `TVDBClient(BaseAPIClient)` and `TMDBClient(BaseAPIClient)` only implement domain-specific methods.

**Impact:** Eliminates ~150 lines of duplication. Makes adding a third API source (e.g., TVMaze) trivial.

---

### 6. Gap Finder Duplication (~40-50% Parallel Logic)

**Files:** `src/complexionist/gaps/movies.py` (294 lines), `src/complexionist/gaps/episodes.py` (372 lines)
**Risk:** Moderate maintenance burden

Both follow the same workflow:

1. Get library sections from Plex
2. Iterate items with progress callbacks
3. Look up metadata via API
4. Compare owned vs available
5. Build results with retry logic

The callback signature, error handling pattern, and retry decorator usage are identical.

**Suggestion:** A `BaseGapFinder` could hold the shared workflow (progress tracking, retry decorator, error logging, library iteration). Subclasses override the domain-specific parts (what to look up, how to compare). This is a larger refactor — worth doing after the API client base class since they're related.

**Impact:** Moderate. The two finders don't change often, so the duplication is tolerable for now.

---

### 7. Unbounded Cache Growth

**File:** `src/complexionist/cache.py`
**Risk:** Disk/memory growth over time

The cache file grows indefinitely. Expired entries are only skipped on read — never purged from the file. A user scanning large libraries could accumulate thousands of stale entries.

**Suggestion:** Add a `purge_expired()` method that removes entries past their TTL. Run it during idle time (e.g., after a scan completes, or on a background timer when the app is sitting on the dashboard) rather than at startup — this avoids adding to boot time:

```python
def purge_expired(self) -> int:
    """Remove all expired entries. Returns count removed."""
    ...
```

**Impact:** Prevents slow cache loads and unnecessary disk usage for power users.

---

### 8. File Write Error Handling (Cache Save)

**File:** `src/complexionist/cache.py` — `_save()`
**Risk:** Silent data loss

If `_save()` fails (disk full, permissions, file locked), the exception propagates up and potentially crashes mid-scan. There's no atomic write pattern (write to temp → rename).

**Suggestion:** Write to a `.tmp` file first, then rename. Catch `OSError` and log instead of crashing:

```python
def _save(self) -> None:
    tmp = self._path.with_suffix(".tmp")
    try:
        tmp.write_text(json.dumps(self._data, indent=2))
        tmp.replace(self._path)
    except OSError as e:
        logger.error("Failed to save cache: %s", e)
```

**Impact:** Prevents data loss and mid-scan crashes on disk issues.

---

## Low Impact / Nice-to-Have

### 9. Boot Time Is Already Good

Boot time is well-optimized. Lazy imports are used in 7+ places throughout the codebase (e.g., importing `Cache`, `rich`, API clients only when needed). The Flet framework itself is the main startup cost.

**No action needed.** Current approach is excellent.

---

### 10. Connection Pooling Already in Place

Both API clients use `httpx.Client` (connection-pooled, HTTP/2 capable). No improvements needed here.

---

### 11. Collection Folder Sanitization

File system path sanitization for collection folders uses basic character replacement. Works well for Windows/macOS/Linux. Could be more robust with a dedicated library but the current approach covers all practical cases.

**No action needed.**

---

## Dependencies Analysis

### Current Versions vs Latest Available

| Package | Pinned | Current Latest | Status | Notes |
|---------|--------|----------------|--------|-------|
| **plexapi** | >=4.17.0 | 4.18.0 | **Review** | 4.18.0 has API changes — test before upgrading |
| **httpx** | >=0.28.0 | 0.28.1 | OK | Patch release, safe to update |
| **click** | >=8.3.0 | 8.3.7 | OK | Stable, no issues |
| **python-dotenv** | >=1.0.0 | 1.1.0 | OK | Minor release, backward compatible |
| **pydantic** | >=2.12.0 | 2.12.1 | OK | Patch release |
| **rich** | >=14.0.0 | 14.0.1 | OK | Trivial patch |
| **pyyaml** | >=6.0.0 | 6.0.2 | OK | Patch release |
| **flet** | >=0.80.0 | 0.80.1 | OK | Patch release, safe |
| **ruff** | >=0.14.0 | 0.14.2 | OK | Minor lint rule additions |
| **pytest** | >=9.0.0 | 9.0.1 | OK | Patch |
| **pytest-asyncio** | >=0.23.0 | 0.26.0 | **Tighten** | Wide range — pin to >=0.26.0 |
| **mypy** | >=1.19.0 | 1.19.0 | OK | Current |
| **pyinstaller** | >=6.18.0 | 6.18.0 | OK | Current |

### Dependency Recommendations

1. **plexapi 4.18.0** — Has breaking changes in library section iteration. Test thoroughly before bumping the minimum. Consider pinning `>=4.17.0,<4.19.0` until validated.

2. **pytest-asyncio** — The `>=0.23.0` floor is very wide. The async mode configuration changed in 0.24+. Pin to `>=0.26.0` to avoid surprises.

3. **Pygments exclusion** — Pygments is pulled in by `rich` but only used for syntax highlighting (not needed in this app). Excluding it from the PyInstaller build could save ~8MB:
   ```python
   excludes=['mypy', 'pip', 'setuptools', 'wheel', 'pkg_resources', 'tzdata', 'pygments'],
   ```

4. **No upper bounds** — All deps use `>=` with no ceiling. This is fine for a consumer app that's built and distributed as an exe, but could cause issues if someone installs from source and gets a breaking update. Consider adding upper bounds for `plexapi` and `flet` specifically, as these are most likely to have breaking changes.

---

## Summary — Priority Order

| # | Finding | Effort | Risk | Action | Status |
|---|---------|--------|------|--------|--------|
| 1 | Non-thread-safe cache | Small | High | Add RLock | **Done** |
| 2 | YAML config no error handling | Small | High | Add try/except | **Done** |
| 3 | Path traversal in map_plex_path | — | Low | Informational | N/A |
| 4 | Results screen duplication | Medium | Medium | Extract shared builder | **Done** |
| 5 | API client duplication | Medium | Medium | Extract BaseAPIClient | **Done** |
| 6 | Gap finder duplication | Large | Low | Extract BaseGapFinder | Deferred (not worth the abstraction) |
| 7 | Unbounded cache growth | Small | Medium | Add purge_expired() | **Done** (idle-time pruning) |
| 8 | Cache save not atomic | Small | Medium | Write-then-rename | **Done** |
| 9 | Exclude Pygments from build | Trivial | — | Save ~8MB on exe | **Done** |
| 10 | Tighten pytest-asyncio pin | Trivial | — | >=0.26.0 | **Done** |
| 11 | Validate plexapi 4.18.0 compat | Medium | — | Test before bumping | **Done** (all stable API usage) |
