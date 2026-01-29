# ComPlexionist - Development TODO

## Current Focus: Phase 9 - GUI (v2.0)

Planning GUI development for a more user-friendly interface.

---

## Completed Phases

### Phase 0: Project Setup ✓
- [x] Initialize Python project with `pyproject.toml`
- [x] Set up virtual environment
- [x] Install core dependencies
- [x] Create package structure (`src/complexionist/`)
- [x] Create `.env.example`
- [x] Set up Ruff linting
- [x] Create CLI entry point

### Phase 1: Plex Integration ✓
- [x] Implement Plex authentication (token-based)
- [x] List available libraries
- [x] Extract movies with TMDB IDs
- [x] Extract TV shows with TVDB GUIDs
- [x] Extract episodes with season/episode numbers
- [x] Handle missing external IDs gracefully

### Phase 2: TMDB Integration ✓
- [x] Create TMDB API client
- [x] Implement movie details endpoint (get collection info)
- [x] Implement collection endpoint (get all movies)
- [x] Handle rate limiting with backoff utility

### Phase 3: Movie Gap Detection ✓
- [x] Create `MovieGapFinder` class in `gaps/movies.py`
- [x] Build owned movie set from Plex (by TMDB ID)
- [x] Query TMDB for collection membership for each movie
- [x] Deduplicate collections (many movies share same collection)
- [x] Fetch full collections from TMDB
- [x] Filter out future releases (release_date > today)
- [x] Compare and identify missing movies
- [x] Generate missing movies report (grouped by collection)
- [x] Wire into CLI `movies` command
- [x] Add progress indicators

### Phase 4: TVDB Integration ✓
- [x] Create TVDB v4 API client
- [x] Implement login/token flow (Bearer token)
- [x] Implement series episodes endpoint (paginated)
- [x] Handle rate limiting

### Phase 5: Episode Gap Detection ✓
- [x] Create `EpisodeGapFinder` class in `gaps/episodes.py`
- [x] Build owned episode map from Plex
- [x] Parse multi-episode filenames (S02E01-02, S02E01-E02, S02E01E02)
- [x] Query TVDB for complete episode lists
- [x] Filter: future episodes, specials (Season 0)
- [x] Compare and generate missing episodes report
- [x] Wire into CLI `episodes` command
- [x] Add progress indicators
- [x] Text/JSON/CSV output formats

### Phase 6: CLI Polish (v1.0) ✓
- [x] Wire movie gap detection into CLI `movies` command
- [x] JSON output format (movies)
- [x] CSV output format (movies)
- [x] Progress indicators with Rich
- [x] Wire episode gap detection into CLI `episodes` command
- [x] JSON output format (episodes)
- [x] CSV output format (episodes)
- [x] Configuration file support (YAML)
- [x] Show exclusion list (`--exclude-show` and config)
- [x] Recent episode threshold (`--recent-threshold`)
- [x] `--quiet` flag for minimal output
- [x] `--min-collection-size` for filtering small collections
- [x] Collection exclusion list (config)

### Phase 7: Caching (v1.1) ✓
- [x] Design cache storage (JSON files)
- [x] Implement TTL-based caching (7 days TMDB, 24h TVDB)
- [x] `--no-cache` flag implementation
- [x] `cache clear` command
- [x] `cache stats` command

### Phase 7.5: CI/CD & Versioning ✓
- [x] Implement dynamic versioning (MAJOR.MINOR.{commit_count})
- [x] Create GitHub Actions CI workflow (test + lint)
- [x] Create GitHub Actions build workflow (Windows executable)
- [x] Add CI badges to README

### Phase 7.6: UX Improvements (v1.2) ✓
- [x] First-run setup wizard with interactive prompts
- [x] INI config format (`complexionist.ini`) replacing `.env`
- [x] Config search order: exe dir → cwd → home dir
- [x] `--library` flag for library selection
- [x] `--min-owned` flag for collection filtering
- [x] `--dry-run` flag for config validation
- [x] `--no-csv` flag (CSV auto-saved by default)
- [x] Cache redesign: single JSON file with fingerprint invalidation
- [x] Summary reports with completion score, API stats, cache metrics
- [x] Command rename: `episodes` → `tv`
- [x] Top 3 shows with most gaps in TV summary

### Phase 8: Consolidation (v1.3) ✓
Code cleanup and architectural improvements.

**8.1 CLI Output Consolidation**
- [x] Create `ReportFormatter` base class with `MovieReportFormatter` and `TVReportFormatter`
- [x] Consolidate output methods (`to_json`, `to_csv`, `to_text`, `save_csv`, `show_summary`)
- [x] Move formatters to `src/complexionist/output/` package

**8.2 CLI Command Consolidation**
- [x] Extract progress callback to reusable `_create_progress_updater()` helper
- [x] Keep `movies()` and `tv()` separate (different options make shared executor complex)

**8.3 API Client Base Class**
- [x] Create `src/complexionist/api/` package with base exceptions
- [x] Unify exception hierarchy (`APIError`, `APIAuthError`, `APINotFoundError`, `APIRateLimitError`)
- [x] TMDB/TVDB exceptions inherit from both API base and their specific base
- [x] Create `parse_date()` helper and `cached_api_call()` pattern

**8.4 Model Mixins**
- [x] Create `src/complexionist/models/` package with mixins
- [x] Create `EpisodeCodeMixin` for S01E01 format
- [x] Create `DateAwareMixin` with `is_date_past()` / `is_date_future()` helpers

---

### Phase 8.5: MyPy Cleanup ✓
Fix type errors to make MyPy pass cleanly in CI.

**8.5.1 Quick Fixes**
- [x] Remove unused `type: ignore` comment in `plex/client.py`
- [x] Add `cast()` for Any returns in `plex/client.py`, `cache.py`, `tvdb/client.py`, `tmdb/client.py`
- [x] Add return type annotations in `tvdb/client.py`, `tmdb/client.py`

**8.5.2 Bug Fixes / Type Corrections**
- [x] Fix `first_aired` → `firstAired` field name in `tvdb/client.py`
- [x] Fix `cache.set()` receiving `list[dict]` instead of `dict` in `tvdb/client.py`
- [x] Fix `belongs_to_collection` dict → `TMDBCollectionInfo` in `tmdb/client.py`

---

## Upcoming Phases

### Phase 9a: Flet GUI (v2.0) - IN PROGRESS
Desktop and local web interface using Flet framework.

**9a.1 Project Setup** ✓
- [x] Add `flet` to dependencies in `pyproject.toml`
- [x] Create `src/complexionist/gui/` package
- [x] Add `--gui` and `--web` flags to CLI entry point

**9a.2 Core Framework** ✓
- [x] App shell with navigation (sidebar NavigationRail)
- [x] Theme support (dark mode default, Plex gold accent)
- [x] State management (AppState dataclass with scan results, progress)

**9a.3 Screens** ✓
- [x] Onboarding wizard (first-run setup with connection testing)
- [x] Dashboard/home (quick actions, connection status indicators)
- [x] Library selection (dialog with dropdown before scan)
- [x] Scanning with progress (pubsub-based updates, cancel button, live stats)
- [x] Results display (grouped ExpansionTiles, search filter, owned/missing)
- [x] Settings panel (config path, theme toggle, re-run setup)
- [ ] Help/about

**9a.4 Integration** ✓
- [x] Wire up existing gap finders (MovieGapFinder, EpisodeGapFinder)
- [x] Connect to existing config/cache modules
- [x] Export functionality (CSV, JSON, clipboard via FilePicker)
- [ ] Local web mode (`complexionist --web` opens browser)

**9a.5 Polish**
- [x] Granular progress updates during initialization phases
- [x] Live API stats display (Time, Plex, TMDB/TVDB, Cache hit rate)
- [x] Centralized UI strings file (`gui/strings.py`) for future localization
- [x] Centralized error handler (`gui/errors.py`) with friendly snackbar messages
- [x] Window state persistence (`gui/window_state.py`) - saves/loads size/position to INI
- [x] Clean window close handling (no asyncio errors on Windows)
- [ ] Keyboard shortcuts

**9a.6 Code Consolidation**
- [x] Consolidate `ScanStats` (gui/state.py) into `ScanStatistics` (statistics.py)
- [x] Move config validation (`has_valid_config()`) to config.py module
- [x] Create `constants.py` for shared PLEX color constant and score thresholds
- [x] Consolidate duration formatting into statistics.py (`duration_str` property)
- [x] Extract score thresholds to shared constants (`get_score_rating()`)
- [x] Create shared connection testing function (`test_connections()` in validation.py)
- [ ] Create `ScanRunner` abstraction for scan execution (deferred - higher risk)
- [x] Add `--use-ignore-list` CLI flag to use ignored items from INI config
- [x] Share `get_friendly_message()` error mapping (moved to `errors.py` module)

**9a.7 Distribution**
- [x] PyInstaller spec file for single-file executable
- [x] Bundle Flet desktop client in exe
- [x] Default to GUI mode, add `--cli` flag for CLI mode

---

### Phase 9b: Browser Extension (v2.1)
Cross-platform browser extension for Chrome/Firefox.

**9b.1 Extension Setup**
- [ ] Create `extension/` directory in repo
- [ ] `manifest.json` (Chrome Manifest V3)
- [ ] TypeScript + esbuild build config
- [ ] Extension popup HTML/CSS

**9b.2 Core Logic (TypeScript)**
- [ ] Plex API client
- [ ] TMDB API client
- [ ] TVDB API client
- [ ] Gap finding logic

**9b.3 UI Components**
- [ ] Popup interface (compact mode selection)
- [ ] Options page (settings/credentials)
- [ ] Results page (full gap display)

**9b.4 Storage**
- [ ] Config in `browser.storage.sync` (syncs across devices)
- [ ] Cache in `browser.storage.local`
- [ ] IndexedDB for large datasets

**9b.5 Publishing**
- [ ] Chrome Web Store submission
- [ ] Firefox Add-ons submission
- [ ] CI/CD workflow for extension builds

---

## Future Optimizations

### Executable Size Optimization (Low Priority)
Current `flet pack` builds produce ~83 MB executables. The original PyInstaller spec file produced ~57 MB locally. Potential areas to investigate:

- **Dev tool exclusions:** mypy (~35 MB), pip (~12 MB), setuptools (~8.5 MB) are bundled but not needed at runtime
- **flet pack limitations:** `--pyinstaller-build-args --exclude-module=mypy` doesn't properly pass exclusion flags
- **Custom spec file:** Could create a hybrid approach using Flet's PyInstaller hook but with manual exclusions
- **tzdata:** Only ~1.5 MB (transitive dep via flet-cli → cookiecutter → arrow) - not significant

Note: The extra size is acceptable since the build works correctly. Only investigate if size becomes a user concern.

---

### N+1 Query Pattern
The movie gap finder calls `get_movie()` individually for each movie to check collection membership. Optimizations implemented to reduce API calls:

**Implemented:**
- [x] Conditional TTL based on collection membership:
  - Movies WITH collection: 30 days (collection membership rarely changes)
  - Movies WITHOUT collection: 7 days (might be added to a collection)
  - Collections: 30 days (new movies picked up via movie lookup)
- [x] TMDB doesn't support batch IDs (confirmed via their Trello)

**Not needed:**
- Collection deduplication already implemented (if 5 movies share a collection, we fetch it once)

---

## Documentation

- [x] README.md
- [x] Plex-Background.md
- [x] Reference-Analysis.md
- [x] Specification.md
- [x] Implementation-Plan.md
- [x] Completed.md (updated)
- [ ] User guide
- [ ] API key setup instructions
