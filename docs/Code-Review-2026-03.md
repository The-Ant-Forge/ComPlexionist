# Code Review - March 2026

**Scope:** Full codebase review covering `src/complexionist/`, `tests/`, build config, and docs.

## Summary Table

| # | Category | Description | Action | Impact | Effort | Risk |
|---|----------|-------------|--------|--------|--------|------|
| 1 | Dead code | `save_default_yaml_config()` and `get_plex_server()` in config.py never called | Remove | Med | Low | Low |
| 2 | Dead code | `PlexSeason` model defined but never instantiated | Remove | Low | Low | Low |
| 3 | Dead code | `EpisodeCodeMixin` and `DateAwareMixin` exported but never used | Remove | Low | Low | Low |
| 4 | Duplication | Frozen exe path check repeated 3 times (config.py, gui/errors.py, gui/app.py) | Refactor | Med | Low | Low |
| 5 | Duplication | `ScanStatistics` imported inline from function scope in 13 places | Refactor | Med | Low | Low |
| 6 | Duplication | ~~TMDB/TVDB clients duplicate inline cache check+record pattern~~ **Skipped** — conditional TTL makes generic helper a poor fit | ~~Refactor~~ | High | Med | Med |
| 7 | Duplication | `is_released` / `is_aired` — identical date-check logic in TMDB and TVDB models | Refactor | Low | Low | Low |
| 8 | Duplication | TMDB/TVDB client `__init__` duplicates config loading + key validation | Refactor | Med | Low | Low |
| 9 | Error handling | Bare `except Exception:` silently returns defaults in library_state.py, window_state.py | Refactor | High | Low | Low |
| 10 | Error handling | Inconsistent error handling in gap finders (movies.py vs episodes.py) | Refactor | Med | Low | Low |
| 11 | Error handling | API base error response parsing swallows nested exception silently | Refactor | Med | Low | Low |
| 12 | Security | API error messages in setup.py could leak credentials in exception text | Refactor | Med | Low | Low |
| 13 | Robustness | PlexClient accesses private `_server._session` for cleanup — fragile | Refactor | Med | Low | Med |
| 14 | Robustness | Cache write failure is completely silent — no debug logging | Add | Med | Low | Low |
| 15 | Performance | List used instead of set for multi-episode deduplication (episodes.py) | Refactor | Low | Low | Low |
| 16 | Duplication | Dashboard snackbar created inline instead of using gui/errors.py helpers | Refactor | Low | Low | Low |
| 17 | Dependencies | `pyyaml` used only for legacy YAML config migration — consider optional | Refactor | Low | Med | Med |
| 18 | Test gaps | Entire GUI module (14 files) has no tests | Add | High | High | Low |
| 19 | Test gaps | CLI tests are minimal — no actual command execution tested | Add | Med | Med | Low |
| 20 | Test gaps | Output module (report formatting) has no tests | Add | Med | Med | Low |
| 21 | Type safety | `AppState` uses `Any` for `scanning_screen`, `movie_report`, `tv_report` | Refactor | Low | Low | Low |
| 22 | Docs drift | Specification.md predates GUI, multi-server, organize feature | Refactor | Low | Med | Low |
| 23 | Stale docs | Implementation-Plan.md, Reference-Analysis.md, code review v1.md are outdated | Remove | Low | Low | Low |
| 24 | Duplication | Complex path mapping logic in config.py could use pathlib | Refactor | Low | Med | Med |

---

## Detailed Findings

### 1. Dead Code

#### 1.1 Unused functions in config.py (Remove, Impact: Med, Effort: Low, Risk: Low)

Two functions in [config.py](../src/complexionist/config.py) are never called anywhere:

- **`save_default_yaml_config()`** (line 572) — creates a YAML config file, but the project standardized on INI format. Legacy dead code.
- **`get_plex_server()`** (line 633) — retrieves a Plex server config by index, but multi-server support uses `cfg.plex.servers` directly.

**Action:** Delete both functions.

#### 1.2 Unused PlexSeason model (Remove, Impact: Low, Effort: Low, Risk: Low)

[PlexSeason](../src/complexionist/plex/models.py) (line 75) is defined and exported from `plex/__init__.py` but never instantiated. Season handling goes through `PlexShowWithEpisodes` directly.

**Action:** Delete the class and remove from `__init__.py` exports.

#### 1.3 Unused model mixins (Remove, Impact: Low, Effort: Low, Risk: Low)

[EpisodeCodeMixin and DateAwareMixin](../src/complexionist/models/mixins.py) are defined and exported via `models/__init__.py` but never used anywhere. The same logic is implemented inline in the actual models (`MissingEpisode.episode_code`, `TMDBMovie.is_released`).

**Action:** Delete `models/mixins.py` and remove exports from `models/__init__.py`. If the entire `models/` package becomes empty, remove it.

---

### 2. Duplication

#### 2.1 Frozen exe path check repeated 3 times (Refactor, Impact: Med, Effort: Low, Risk: Low)

The `getattr(sys, "frozen", False)` pattern for detecting PyInstaller exe mode appears in:
- [config.py:112](../src/complexionist/config.py) — `get_exe_directory()`
- [gui/errors.py:20](../src/complexionist/gui/errors.py) — `_get_log_file_path()`
- [gui/app.py:739](../src/complexionist/gui/app.py) — assets directory resolution

**Action:** Consolidate into `config.py` with a single `get_exe_directory()` function (already exists) and have the other two use it. The assets case is different (uses `sys._MEIPASS`) so may need a second helper like `get_assets_directory()`.

#### 2.2 ScanStatistics imported inline 13 times (Refactor, Impact: Med, Effort: Low, Risk: Low)

`from complexionist.statistics import ScanStatistics` appears inside function bodies in:
- `api/base.py` (2x), `api/helpers.py` (1x), `plex/client.py` (4x), `cli.py` (2x), `gui/app.py` (1x), `gui/screens/scanning.py` (1x), `output/__init__.py` (1x)

This is done to avoid circular imports, but there are better patterns.

**Action:** Use `TYPE_CHECKING` guard at module level for type annotations. For runtime use, the lazy import is acceptable in api/base.py (which is the base class), but downstream modules (TMDB, TVDB, Plex clients) that inherit from `BaseAPIClient` could get it via the base class instead of re-importing.

#### 2.3 TMDB/TVDB clients duplicate cache logic (Refactor, Impact: High, Effort: Med, Risk: Med)

Both `TMDBClient` and `TVDBClient` have 4 methods each that repeat the same cache check/record pattern:
```python
if self._cache:
    cached = self._cache.get(namespace, category, key)
    if cached:
        self._record_cache_hit(namespace)
        return ModelClass.model_validate(cached)
self._record_cache_miss(namespace, api_call_type)
```

A `cached_api_call()` helper exists in [api/helpers.py:35](../src/complexionist/api/helpers.py) but is not used by these methods, likely because the TTL logic varies per method (e.g., collection membership vs show status affects TTL).

**Action:** Extend `cached_api_call()` to accept a TTL callback, then refactor client methods to use it. This eliminates ~40 lines of duplication and ensures consistent cache statistics recording.

#### 2.4 Identical date-check logic (Refactor, Impact: Low, Effort: Low, Risk: Low)

[TMDBMovie.is_released](../src/complexionist/tmdb/models.py) and [TVDBEpisode.is_aired](../src/complexionist/tvdb/models.py) implement the same "is this date before yesterday?" logic with different property names.

**Action:** Extract a shared `is_before_today(date_value)` utility function. Keep the property names as-is (they're domain-appropriate) but have them call the shared function.

#### 2.5 TMDB/TVDB client __init__ duplication (Refactor, Impact: Med, Effort: Low, Risk: Low)

Both clients duplicate: load API key from config → validate key → create httpx client → set headers. The base class `BaseAPIClient.__init__()` already handles some of this, but the config loading is duplicated.

**Action:** Move config-based API key loading into `BaseAPIClient.__init__()` with a `config_section` parameter.

#### 2.6 Dashboard snackbar bypass (Refactor, Impact: Low, Effort: Low, Risk: Low)

[dashboard.py](../src/complexionist/gui/screens/dashboard.py) creates snackbars inline instead of using the `show_success()`/`show_warning()` helpers from [gui/errors.py](../src/complexionist/gui/errors.py).

**Action:** Replace inline snackbar creation with helper calls.

---

### 3. Error Handling

#### 3.1 Silent exception swallowing (Refactor, Impact: High, Effort: Low, Risk: Low)

Several GUI state persistence modules catch `Exception` and silently return defaults:
- [library_state.py:56](../src/complexionist/gui/library_state.py) — returns empty `LibrarySelection()` on any error
- [library_state.py:88](../src/complexionist/gui/library_state.py) — returns `False` on save failure
- [window_state.py:64](../src/complexionist/gui/window_state.py) — returns default `WindowState()` on any error
- [window_state.py:107](../src/complexionist/gui/window_state.py) — returns `False` on save failure

**Action:** Add `log_error()` calls before returning defaults so failures are diagnosable.

#### 3.2 Inconsistent gap finder error handling (Refactor, Impact: Med, Effort: Low, Risk: Low)

[movies.py](../src/complexionist/gaps/movies.py) catches only `TMDBNotFoundError` and silently continues. [episodes.py](../src/complexionist/gaps/episodes.py) catches both `TVDBNotFoundError` (continue) and `TVDBError` (log + continue).

**Action:** Align both gap finders: catch the specific NotFound error to skip, catch the broader API error to log and continue.

#### 3.3 API error response parsing (Refactor, Impact: Med, Effort: Low, Risk: Low)

In [api/base.py](../src/complexionist/api/base.py) (~line 121), the nested exception when parsing error JSON is silently caught. If `response.json()` fails and `response.text` is empty, the user gets "Unknown error" with no diagnostic info.

**Action:** Include the HTTP status code in the fallback message: `f"HTTP {response.status_code}: {response.text or 'Unknown error'}"`.

---

### 4. Security

#### 4.1 API error messages could leak credentials (Refactor, Impact: Med, Effort: Low, Risk: Low)

In [setup.py](../src/complexionist/setup.py), connection test failures return the raw exception message: `f"Error: {e}"`. If the API returns error text that includes the submitted credentials, they could be exposed in the UI.

**Action:** Catch specific exception types (timeout, connection error, auth error) and return generic messages. Only include `str(e)` for unexpected exceptions after stripping any URL parameters.

---

### 5. Robustness

#### 5.1 Private attribute access for PlexServer cleanup (Refactor, Impact: Med, Effort: Low, Risk: Med)

In [gui/app.py](../src/complexionist/gui/app.py) (~line 945), cleanup accesses `plex._server._session.close()` — private attributes of the plexapi library.

**Action:** Add a `close()` method to `PlexClient` that encapsulates this cleanup, so only one place needs updating if plexapi internals change.

#### 5.2 Silent cache write failure (Add, Impact: Med, Effort: Low, Risk: Low)

In [cache.py](../src/complexionist/cache.py) (~line 256), if both the atomic rename and direct write fail, the failure is completely silent. The cache is non-critical, but users can't diagnose why their cache isn't persisting.

**Action:** Add `logger.debug()` logging for the failure case.

---

### 6. Performance

#### 6.1 List instead of set for episode deduplication (Refactor, Impact: Low, Effort: Low, Risk: Low)

In [episodes.py](../src/complexionist/gaps/episodes.py) (~line 67), multi-episode deduplication uses:
```python
if (season, ep_num) not in episodes:  # O(n) list scan
    episodes.append((season, ep_num))
```

**Action:** Use a set for O(1) lookups, convert to list at the end if needed.

---

### 7. Dependencies

#### 7.1 PyYAML for legacy config only (Refactor, Impact: Low, Effort: Med, Risk: Med)

`pyyaml` is a runtime dependency but is only used in one function for backwards-compatible YAML config loading. All new configs use INI format.

**Action:** Consider making it optional (try/except on import) with a user-facing message to install it if a YAML config is detected. Alternatively, keep it as-is — it's small (~240KB) and the migration path is important. **Recommend: defer this, low value.**

---

### 8. Test Gaps

#### 8.1 GUI module untested (Add, Impact: High, Effort: High, Risk: Low)

The entire `gui/` package (14 files, ~5000+ lines including settings.py at 1600 lines and results.py at 1200 lines) has zero test coverage. GUI testing with Flet is non-trivial, but at minimum the state management and non-UI logic could be unit tested.

**Action:** Add tests for `AppState` operations, `WindowState` serialization, `LibrarySelection` serialization, and any pure logic extracted from screens. Full UI testing is out of scope.

#### 8.2 CLI tests minimal (Add, Impact: Med, Effort: Med, Risk: Low)

[test_cli.py](../tests/test_cli.py) only tests help, version, and command existence. No actual command execution with mocked APIs.

**Action:** Add tests that invoke CLI commands with mocked Plex/TMDB/TVDB responses.

#### 8.3 Output module untested (Add, Impact: Med, Effort: Med, Risk: Low)

[output/__init__.py](../src/complexionist/output/__init__.py) (489 lines) handles JSON, CSV, and text report formatting with no tests.

**Action:** Add tests for `MovieReportFormatter` and `TVReportFormatter` with sample data.

---

### 9. Type Safety

#### 9.1 AppState uses Any types (Refactor, Impact: Low, Effort: Low, Risk: Low)

In [gui/state.py](../src/complexionist/gui/state.py), three fields use `Any`:
- `scanning_screen: Any | None` — should be `ScanningScreen | None`
- `movie_report: Any | None` — should be `MovieGapReport | None`
- `tv_report: Any | None` — should be `EpisodeGapReport | None`

**Action:** Use `TYPE_CHECKING` imports and proper type annotations.

---

### 10. Documentation

#### 10.1 Specification.md outdated (Refactor, Impact: Low, Effort: Med, Risk: Low)

[Specification.md](../docs/Specification.md) predates the GUI, multi-server support, collection organization, and ignore lists. It describes a CLI-only architecture.

**Action:** Add a "GUI Features (v2.0)" section and update the caching description to match the fingerprint-based invalidation.

#### 10.2 Stale planning docs (Remove, Impact: Low, Effort: Low, Risk: Low)

These docs served their purpose during initial development and are now superseded:
- `docs/Implementation-Plan.md` — superseded by Specification.md and Completed.md
- `docs/Reference-Analysis.md` — initial research, no longer actionable
- `docs/code review v1.md` — outdated by this review

**Action:** Archive or delete. The historical value is minimal since `Completed.md` captures what was built and why.

---

## Out of Scope (belongs in TODO.md)

These were identified during review but are feature work, not consolidation:

- **Parallel TMDB collection lookups** using ThreadPoolExecutor for large libraries
- **Pagination for large Plex libraries** (10k+ items currently loaded all at once)
- **Python logging module** integration instead of ad-hoc file logging
- **Centralized error handling conventions** documented in CLAUDE.md
