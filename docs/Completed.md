# ComPlexionist - Completed Work

This file is a durable record of finished work. Each entry captures what shipped, why it mattered, and where it lives.

See `TODO.md` for forward-looking work items.

---

## Dependency Updates & Flet 0.83 Upgrade (2026-03-28)

**Why:** Keep dependencies current. Flet 0.83 brings sparse prop tracking for faster UI diffs — noticeable improvement during scans and on the results screen.

**What we did:**
- Upgraded flet 0.82.2 → 0.83.0, plexapi → 4.18.1, ruff → 0.15.8, rich → 14.3.3, python-dotenv → 1.2.2
- Updated plexapi pin from `>=4.17.0` to `>=4.18.0`
- Rewrote `complexionist.spec` for Flet 0.83's new desktop client distribution model (client binary no longer in wheel; spec creates zip from `~/.flet/client/` cache at build time)
- Updated CLAUDE.md build instructions for new Flet client bundling workflow

**Key files:** `pyproject.toml`, `complexionist.spec`, `CLAUDE.md`

**Gotchas:**
- `flet-desktop` must be installed separately for builds: `uv pip install flet-desktop==<version>`
- Flet client must be cached before building (run `uv run complexionist` once)
- Exe extracts bundled client zip to `~/.flet/client/` on first launch

---

## Code Consolidation Phase (2026-03-06)

**Why:** Reduce dead code, duplication, and silent failures across the codebase. Improve test coverage for GUI state and output formatting.

**What we did:**
- Removed dead code: `save_default_yaml_config()`, `get_plex_server()`, `PlexSeason` model, entire `models/` package (unused mixins), stale docs
- Consolidated frozen exe path checks into `is_frozen()`, `get_exe_directory()`, `get_assets_directory()` in config.py
- Added `_resolve_api_key()` and `_config_section` to BaseAPIClient (eliminates duplicate init logic in TMDB/TVDB)
- Added `is_date_past()` shared utility, replacing duplicated date comparison in TMDB/TVDB models
- Added `PlexClient.close()` method (encapsulates private `_server._session` access)
- Added `_record_plex_api_call()` static helper (replaces 4 inline ScanStatistics blocks)
- Added `log_error()` to silent exception handlers in library_state.py, window_state.py
- Improved error messages: `"HTTP {status_code}"` fallback instead of `"Unknown error"`, generic connection errors hide tracebacks
- Added debug logging for cache write failures
- Used set-based deduplication in episode gap finder (O(1) vs O(n))
- Added `TMDBError` catch in movie gap finder (was only catching `TMDBNotFoundError`)
- Made PyYAML optional (moved to `[project.optional-dependencies]`, conditional import)
- Properly typed `AppState` with `TYPE_CHECKING` imports
- Added 23 GUI state/utility tests and 18 output formatter tests (41 new, 245 total)
- Updated Specification.md (removed stale model mixins, fixed cache strategy table, updated project structure)

**Key files:**
- `src/complexionist/config.py` — `is_frozen()`, `get_exe_directory()`, `get_assets_directory()`, optional PyYAML
- `src/complexionist/api/base.py` — `_resolve_api_key()`, `_config_section`
- `src/complexionist/utils.py` — `is_date_past()`
- `src/complexionist/plex/client.py` — `close()`, `_record_plex_api_call()`
- `tests/test_gui_state.py`, `tests/test_output.py` — new test files
- `docs/Code-Review-2026-03.md` — review document with 24 findings

**Decisions:**
- Skipped #6 (generic `cached_api_call()` helper) — conditional TTL logic in TMDB/TVDB methods makes the abstraction a poor fit

---

## Complete Collection Organization & Performance (2026-03-03)

**Why:** When a movie collection was fully owned, it disappeared from results — so there was no way to organize scattered files. Also, the organize dialog was sluggish due to full-page re-renders on every interaction.

**What we did:**
- Added `is_complete` flag and `movies_in_different_folders` property to `CollectionGap` model
- Complete-but-disorganized collections now appear in results with "Complete X of X" subtitle
- Added "Organised" (green tick) indicator for collections with movies already grouped
- Folder detection handles two Plex layouts: `Library/CollectionFolder/file.mkv` and `Library/CollectionFolder/MovieFolder/file.mkv`
- Refactored organize dialog to use `dialog.update()` instead of `page.update()`, eliminating full-page re-renders
- Pre-created dialog and snackbar in overlay during `build()` for instant open/close
- Added background threading for safety checks with in-dialog progress
- Added move progress bar with per-file status in the same dialog
- Added double-click protection and modal focus
- Removed unused `overview` fields from TMDB/TVDB/gap models to reduce cache size

**Key files:**
- `src/complexionist/gaps/models.py` — `movies_in_different_folders`, `is_complete`
- `src/complexionist/gaps/movies.py` — complete collection detection in gap finder
- `src/complexionist/gui/screens/results.py` — organize dialog refactor, targeted updates
- `src/complexionist/output/__init__.py` — CLI output for complete collections
- `src/complexionist/tmdb/models.py`, `tvdb/models.py` — overview field removal
- `tests/test_gaps.py` — 7 new tests for folder detection and complete collections

**Gotchas:**
- `page.update()` diffs the entire control tree — on results pages with hundreds of ExpansionTiles this takes 4-5 seconds. Use `control.update()` for targeted updates wherever possible.
- Setting `on_click` from a background thread doesn't register with Flutter — set handlers on the main thread and use flags/closures for state.
- Pre-creating overlay controls (dialogs, snackbars) during `build()` avoids repeated `page.update()` costs.

---

## Project Setup and Documentation (2025-01-24)

**Why:** Establish project foundation with research and documentation before implementation.

**What we did:**
- Created `README.md` with project overview and feature descriptions
- Created `docs/Plex-Background.md` with comprehensive Plex API research:
  - Authentication methods (X-Plex-Token, JWT, PIN flow)
  - Library architecture and content separation
  - Collections API and the "missing movies" problem
  - TV show hierarchy (Show > Season > Episode)
  - External data sources (TMDB for movies, TVDB for TV)
  - python-plexapi library overview
- Created `docs/TODO.md` with development task breakdown
- Adapted `agents.md` from TVRenamer project for ComPlexionist workflow

**Key files:**
- `README.md`
- `docs/Plex-Background.md`
- `docs/TODO.md`
- `agents.md`

---

## Reference Implementation Analysis (2025-01-24)

**Why:** Understand how existing tools solve similar problems to inform our architecture decisions.

**What we analyzed:**

### Gaps (Movie Collections)
- Java Spring Boot app for finding missing movies in Plex collections
- Uses TMDB API to get complete collection membership
- Key insight: Match movies by TMDB ID, not name
- Key data: `BasicMovie` (Plex) vs `MovieFromCollection` (TMDB)
- Status: No longer maintained, but approach is solid

### WebTools-NG (General Plex Tool)
- Vue.js/Electron app for Plex server management
- Primarily an export tool, NOT a missing content detector
- Limited usefulness for our specific features

### PlexMissingEpisodes (TV Episodes)
- PowerShell script for finding missing TV episodes
- Uses TVDB v4 API for episode listings
- Key insights:
  - Use TVDB GUID from Plex metadata to link shows
  - Handle multi-episode files via filename parsing (S02E01-02)
  - Filter out specials (S00), unaired, and very recent episodes
  - Match by episode number AND name for accuracy
- Output: Simple (`Show - S01E01 - Title`) or detailed (grouped by show/season)

**Recommendations documented:**
- Python recommended (python-plexapi library)
- TMDB for movies (has collection data)
- TVDB v4 for TV (comprehensive episode data)
- CLI-first approach, optional web UI later

**Key files:**
- `docs/Reference-Analysis.md`

---

## Project Specification and Implementation Plan (2025-01-24)

**Why:** Define clear requirements, architecture, and phased development approach before coding.

**What we created:**

### Specification Document
- Tech stack decision: Python 3.11+, plexapi, httpx, Click/Typer
- Feature definitions:
  - F1: Movie Collection Gaps (compare Plex vs TMDB collections)
  - F2: TV Episode Gaps (compare Plex vs TVDB episodes)
  - F3: Caching (reduce API calls on subsequent runs)
- **Key requirement:** Exclude future releases by default (not yet released = false positive)
- CLI interface design with commands and output formats
- Data flow diagrams for both features
- Configuration approach (.env + optional YAML)
- Project structure (src/complexionist/ package layout)
- Success criteria for v1.0, v1.1, v2.0

### Implementation Plan
- 8 phases from setup to GUI
- Phase 0: Project setup
- Phase 1: Plex integration
- Phase 2-3: TMDB + movie gap detection
- Phase 4-5: TVDB + episode gap detection
- Phase 6: CLI polish (v1.0)
- Phase 7: Caching (v1.1)
- Phase 8: GUI (v2.0)
- Testing strategy and risk mitigation

**Key files:**
- `docs/Specification.md`
- `docs/Implementation-Plan.md`

---

## Phase 0: Project Setup (2025-01-24)

**Why:** Establish runnable Python project with CLI scaffolding.

**What we did:**
- Created `pyproject.toml` with dependencies:
  - `plexapi` - Plex Media Server integration
  - `httpx` - Async HTTP client for TMDB/TVDB
  - `click` - CLI framework
  - `rich` - Pretty terminal output
  - `pydantic` - Data validation/models
  - `python-dotenv` - Environment variables
  - Dev: `pytest`, `ruff`, `mypy`
- Created package structure: `src/complexionist/` with subpackages
  - `plex/`, `tmdb/`, `tvdb/`, `gaps/`, `output/`
- Created CLI entry point with commands:
  - `movies` - Find missing movies from collections
  - `episodes` - Find missing episodes from TV shows
  - `scan` - Run both scans
  - `config` - Manage configuration
  - `cache` - Manage API cache
- Created `.env.example` with credential templates
- Set up Ruff linting (all checks passing)
- Created initial test suite (6 tests)

**Key files:**
- `pyproject.toml`
- `src/complexionist/cli.py`
- `.env.example`
- `tests/test_cli.py`

---

## Phase 1: Plex Integration (2025-01-24)

**Why:** Connect to Plex Media Server and extract library data with external IDs.

**What we did:**
- Created `PlexClient` using python-plexapi:
  - Token-based authentication (env var or parameter)
  - URL normalization (adds http:// if missing)
  - Connection testing
- Library management:
  - List all libraries with type detection (movie/show)
  - Filter movie libraries vs TV libraries
- Movie extraction:
  - Get all movies from a library
  - Extract TMDB ID, IMDB ID from Plex GUIDs
  - `has_tmdb_id` property for filtering
- TV show extraction:
  - Get all shows from a library
  - Extract TVDB ID, TMDB ID from Plex GUIDs
  - `has_tvdb_id` property for filtering
- Episode extraction:
  - Get all episodes for a show
  - Extract season/episode numbers
  - Extract file paths (for multi-episode detection later)
  - `episode_code` property (e.g., "S01E05")
  - `PlexShowWithEpisodes` model with season grouping

**Data models (Pydantic):**
- `PlexLibrary`: key, title, type, is_movie_library, is_tv_library
- `PlexMovie`: rating_key, title, year, tmdb_id, imdb_id
- `PlexShow`: rating_key, title, year, tvdb_id, tmdb_id
- `PlexEpisode`: season_number, episode_number, file_path
- `PlexShowWithEpisodes`: show with episodes, seasons dict

**Error handling:**
- `PlexAuthError` - Missing URL/token or invalid token
- `PlexConnectionError` - Connection failures
- `PlexNotFoundError` - Library/item not found

**Tested against real Plex server "Holodeck":**
- Movies: 5,432 (99.2% with TMDB ID)
- TV Shows: 1,290 (100% with TVDB ID)

**Key files:**
- `src/complexionist/plex/client.py`
- `src/complexionist/plex/models.py`
- `tests/test_plex.py` (17 tests)

---

## Phase 2: TMDB Integration (2025-01-24)

**Why:** Query TMDB for movie collection data to identify gaps.

**What we did:**
- Created `TMDBClient` with httpx:
  - API key authentication (env var or parameter)
  - Proper error handling with exception chaining
- Movie details endpoint (`GET /movie/{id}`):
  - Returns `TMDBMovieDetails` with `belongs_to_collection`
  - `collection_id` and `collection_name` properties
- Collection endpoint (`GET /collection/{id}`):
  - Returns `TMDBCollection` with all movies
  - `released_movies` property filters out future releases
  - `movie_count` property
- Collection search endpoint for name-based lookup
- Connection testing

**Data models (Pydantic):**
- `TMDBMovie`: id, title, release_date, is_released, year
- `TMDBMovieDetails`: + belongs_to_collection
- `TMDBCollection`: id, name, parts[], movie_count, released_movies
- `TMDBCollectionInfo`: basic collection reference

**Error handling:**
- `TMDBAuthError` - Invalid API key (401)
- `TMDBNotFoundError` - Resource not found (404)
- `TMDBRateLimitError` - Rate limited (429), includes retry_after

**Utilities:**
- `retry_with_backoff` decorator for rate limiting

**Key files:**
- `src/complexionist/tmdb/client.py`
- `src/complexionist/tmdb/models.py`
- `src/complexionist/utils.py`
- `tests/test_tmdb.py` (14 tests)

---

## Phase 3: Movie Gap Detection (2025-01-25)

**Why:** Identify missing movies from collections by comparing Plex library against TMDB data.

**What we did:**
- Created `MovieGapFinder` class that orchestrates gap detection:
  - Gets all movies from Plex with TMDB IDs
  - Queries TMDB for collection membership for each movie
  - Deduplicates collections (many movies share same collection)
  - Fetches full collection data from TMDB
  - Filters out future releases by default (`--include-future` flag)
  - Compares owned movies against collection movies to find gaps
  - Supports progress callback for Rich progress indicators

- Created gap report models:
  - `MissingMovie`: TMDB ID, title, release date, year, overview
  - `CollectionGap`: Collection info with owned/missing counts and movies
  - `MovieGapReport`: Full scan report with summary statistics

- Wired into CLI `movies` command:
  - Rich progress indicators during scanning
  - Text output: Formatted table grouped by collection
  - JSON output: Structured data for machine consumption
  - CSV output: Spreadsheet-compatible format
  - Proper error handling for Plex/TMDB connection issues

**Data flow:**
1. Connect to Plex → Get all movies with TMDB IDs
2. For each movie → Query TMDB for collection membership
3. Deduplicate collections
4. For each collection → Fetch full movie list from TMDB
5. Filter future releases (unless `--include-future`)
6. Compare owned vs collection → Identify missing
7. Generate report sorted by missing count

**Key files:**
- `src/complexionist/gaps/movies.py` - MovieGapFinder class
- `src/complexionist/gaps/models.py` - Gap report models
- `src/complexionist/gaps/__init__.py` - Module exports
- `src/complexionist/cli.py` - CLI command with Rich output
- `tests/test_gaps.py` (15 tests)

---

## Phase 4: TVDB Integration (2025-01-25)

**Why:** Query TVDB for complete episode listings to identify gaps in TV shows.

**What we did:**
- Created `TVDBClient` with two-step authentication:
  - POST API key to `/login` to get Bearer token
  - Use Bearer token for subsequent requests
  - Automatic re-authentication on token expiry
- Implemented series endpoints:
  - `get_series()` - Basic series information
  - `get_series_episodes()` - All episodes with automatic pagination
  - `get_series_with_episodes()` - Combined series + episodes
  - `search_series()` - Search by name
- Rate limiting support with retry capability

**Data models (Pydantic):**
- `TVDBEpisode`: id, series_id, name, season/episode numbers, aired date
  - `episode_code` property (e.g., "S01E05")
  - `is_aired` property for filtering future episodes
  - `is_special` property for Season 0 detection
- `TVDBSeries`: id, name, slug, status, first_aired, year
- `TVDBSeriesExtended`: Series + episodes with filtering methods
  - `aired_episodes`, `regular_episodes`, `aired_regular_episodes`
  - `episodes_by_season()` for grouping

**Error handling:**
- `TVDBAuthError` - Invalid API key or expired token (401)
- `TVDBNotFoundError` - Resource not found (404)
- `TVDBRateLimitError` - Rate limited (429), includes retry_after

**Key files:**
- `src/complexionist/tvdb/client.py` - TVDBClient class
- `src/complexionist/tvdb/models.py` - TVDB data models
- `src/complexionist/tvdb/__init__.py` - Module exports
- `tests/test_tvdb.py` (20 tests)

---

## Phase 5: Episode Gap Detection (2025-01-25)

**Why:** Identify missing TV episodes by comparing Plex library against TVDB episode data.

**What we did:**
- Created `EpisodeGapFinder` class that orchestrates gap detection:
  - Gets all TV shows from Plex with TVDB IDs
  - For each show, fetches episodes from Plex
  - Queries TVDB for complete episode list
  - Filters out future episodes (default) and specials/Season 0 (default)
  - Compares owned episodes against TVDB episodes to find gaps
  - Supports progress callback for Rich progress indicators

- Created multi-episode filename parsing:
  - Parses `S02E01-02` (dash with numbers)
  - Parses `S02E01-E02` (dash with E prefix)
  - Parses `S02E01E02` (consecutive E numbers)
  - Marks multiple episodes as owned from single files

- Created episode gap report models:
  - `MissingEpisode`: TVDB ID, season/episode numbers, title, aired date
  - `SeasonGap`: Missing episodes within a single season
  - `ShowGap`: TV show with missing episodes across seasons
  - `EpisodeGapReport`: Full scan report with summary statistics

- Wired into CLI `episodes` command:
  - Rich progress indicators during scanning
  - Text output: Formatted display grouped by show/season
  - JSON output: Structured data for machine consumption
  - CSV output: Spreadsheet-compatible format
  - `--include-future` flag to include unaired episodes
  - `--include-specials` flag to include Season 0

**Data flow:**
1. Connect to Plex → Get all TV shows with TVDB IDs
2. For each show → Get episodes from Plex (build owned set)
3. Parse multi-episode filenames → Mark additional episodes as owned
4. Query TVDB → Get complete episode list
5. Filter future/specials (unless flags set)
6. Compare owned vs TVDB → Identify missing
7. Generate report sorted by missing count

**Key files:**
- `src/complexionist/gaps/episodes.py` - EpisodeGapFinder class, multi-episode parsing
- `src/complexionist/gaps/models.py` - Episode gap report models
- `src/complexionist/gaps/__init__.py` - Updated module exports
- `src/complexionist/cli.py` - CLI command with Rich output
- `tests/test_gaps.py` - 24 new tests (9 models, 6 parsing, 9 finder)

---

## Phase 6: CLI Polish (2025-01-25)

**Why:** Polish the CLI experience with configuration file support, content exclusions, and filtering options for v1.0 release.

**What we did:**

### Configuration File Support (YAML)
- Created `config.py` module with Pydantic models
- Config file search: `./config.yaml`, `~/.complexionist/config.yaml`
- Environment variable interpolation (`${VAR}` syntax)
- Config sections: plex, tmdb, tvdb, options, exclusions
- CLI commands: `config show`, `config path`, `config init`

### Show/Collection Exclusion Lists
- `EpisodeGapFinder`: Skip shows by title (case-insensitive)
- `MovieGapFinder`: Skip collections by name (case-insensitive)
- CLI: `--exclude-show` option (can be used multiple times)
- Config: `exclusions.shows` and `exclusions.collections` lists

### Recent Episode Threshold
- Filter out episodes aired within N hours
- `EpisodeGapFinder`: `recent_threshold_hours` parameter
- CLI: `--recent-threshold` option
- Config default: 24 hours

### Minimum Collection Size
- Filter out small collections (default: 2 movies)
- `MovieGapFinder`: `min_collection_size` parameter
- CLI: `--min-collection-size` option

### Quiet Mode
- `--quiet` / `-q` flag on main command
- Suppresses progress indicators
- Shows only results

**Data models (Pydantic):**
- `PlexConfig`: url, token
- `TMDBConfig`: api_key
- `TVDBConfig`: api_key, pin
- `OptionsConfig`: exclude_future, exclude_specials, recent_threshold_hours, min_collection_size
- `ExclusionsConfig`: shows[], collections[]
- `AppConfig`: All of the above

**Key files:**
- `src/complexionist/config.py` - Configuration module
- `src/complexionist/cli.py` - Updated CLI with new options
- `src/complexionist/gaps/movies.py` - min_collection_size, excluded_collections
- `src/complexionist/gaps/episodes.py` - recent_threshold_hours, excluded_shows
- `tests/test_config.py` (18 tests)
- `tests/test_gaps.py` - 10 new tests for exclusions/filtering

---

## Phase 7: Caching (2025-01-25)

**Why:** Reduce redundant API calls, respect rate limits, and speed up subsequent scans.

**What we did:**

### Cache Module
- Created `cache.py` module with file-based JSON caching
- Human-readable cache structure:
  ```
  ~/.complexionist/cache/
  ├── tmdb/
  │   ├── movies/
  │   │   └── {movie_id}.json
  │   └── collections/
  │       └── {collection_id}.json
  └── tvdb/
      └── episodes/
          └── {series_id}_{season_type}.json
  ```
- Each cache file includes metadata:
  - `cached_at`: When the entry was cached
  - `expires_at`: When the entry expires
  - `ttl_hours`: Time-to-live in hours
  - `description`: Human-readable description

### TTL Configuration (per spec)
- TMDB movies: 7 days (168 hours) - rarely change
- TMDB collections: 7 days (168 hours) - new movies are rare
- TVDB episodes: 24 hours - episodes can be added

### Cache Integration
- Updated `TMDBClient`:
  - Optional `cache` parameter in `__init__`
  - `get_movie()` checks/stores cache
  - `get_collection()` checks/stores cache
- Updated `TVDBClient`:
  - Optional `cache` parameter in `__init__`
  - `get_series_episodes()` checks/stores cache

### CLI Commands
- `--no-cache` flag wired through to both `movies` and `episodes` commands
- `cache clear` - Remove all cached entries (with confirmation)
- `cache stats` - Display cache statistics:
  - Total entries and size
  - Breakdown by category (TMDB movies/collections, TVDB episodes)
  - Oldest/newest entry timestamps
  - Expired entry count

### Cache Class API
- `get(namespace, category, key)` - Get cached data if not expired
- `set(namespace, category, key, data, ttl_hours, description)` - Store data
- `delete(namespace, category, key)` - Remove specific entry
- `clear(namespace=None)` - Clear all or specific namespace
- `stats()` - Get `CacheStats` dataclass
- `get_expired_count()` - Count expired entries
- `cleanup_expired()` - Remove expired entries

**Key files:**
- `src/complexionist/cache.py` - Cache module (new)
- `src/complexionist/tmdb/client.py` - Added cache support
- `src/complexionist/tvdb/client.py` - Added cache support
- `src/complexionist/cli.py` - Updated commands with cache
- `tests/test_cache.py` - 25 new tests

---

## Phase 7.5: CI/CD & Versioning (2025-01-25)

**Why:** Automate testing, linting, and executable builds for reliable releases.

**What we did:**

### Dynamic Versioning
- Implemented `MAJOR.MINOR.{commit_count}` versioning scheme
- Version automatically increments with each commit
- `complexionist --version` shows current version

### GitHub Actions CI Workflow
- Created `.github/workflows/ci.yml`
- Runs on push and pull requests to main
- Matrix testing across Python versions
- Ruff linting (style and import checks)
- Full pytest suite

### GitHub Actions Build Workflow
- Created `.github/workflows/build.yml`
- Triggers on version tags (e.g., `v1.2.0`)
- Builds Windows executable using PyInstaller
- Creates GitHub Release with attached executable
- Includes release notes

### PyInstaller Configuration
- Created `complexionist.spec` for reproducible builds
- Hidden imports configured for `plexapi` and `rich._unicode_data` modules
- Single-file executable output

**Key files:**
- `.github/workflows/ci.yml` - CI workflow
- `.github/workflows/build.yml` - Build and release workflow
- `complexionist.spec` - PyInstaller specification
- `README.md` - Added CI badges

---

## Phase 7.6: UX Improvements (2025-01-25)

**Why:** Improve user experience based on initial release feedback, including first-run setup, library selection, better output, and summary statistics.

**What we did:**

### First-Run Experience
- Setup wizard detects missing config on startup
- Interactive prompts for all required credentials:
  - Plex server URL and token (with live connection test)
  - TMDB API key (with live validation)
  - TVDB API key (with live validation)
- Creates `complexionist.ini` with entered values
- Offers to run validation after setup

**Key insight:** Live testing during setup catches typos immediately rather than failing during first scan.

### Configuration System Overhaul
- Switched from `.env` to INI format (`complexionist.ini`)
- More user-friendly than environment variables
- Config search order (portability-focused):
  1. Executable directory (for portable installs)
  2. Current working directory
  3. Home directory (`~/.complexionist/`)
- `.env` still works as fallback for backwards compatibility
- `config init` command creates config interactively
- `config show` displays current configuration

### Library Selection
- Added `--library` / `-l` flag to both `movies` and `tv` commands
- Support for multiple libraries: `--library "Movies" --library "Kids Movies"`
- When no library specified, lists available libraries and prompts for selection
- Helpful for users with multiple movie or TV libraries

### Collection Filtering
- Added `--min-owned` flag for movies command
- Only reports gaps for collections where user owns N+ movies (default: 2)
- Prevents noise from collections where user owns only 1 movie
- Can be set in config file: `min_owned = 2`

### Output Improvements
- CSV files now auto-saved alongside terminal output
- Filename format: `{LibraryName}_movies_gaps_{YYYY-MM-DD}.csv` or `{LibraryName}_tv_gaps_{YYYY-MM-DD}.csv`
- Added `--no-csv` flag to disable automatic CSV
- Detailed results now behind confirmation prompt (lists can be long)

### Cache Redesign
- Removed `--no-cache` flag (cache always enabled for performance)
- Single JSON file: `complexionist.cache.json` (next to config)
- Fingerprint-based invalidation:
  - Computes hash of library item IDs + count
  - Detects when library content changes
  - More reliable than timestamp-based approaches
- Batched cache saves (every 250 changes) to avoid Windows file permission issues
- `cache clear` command to reset cache

**Technical note:** Plex doesn't expose library `updatedAt` timestamps via API, so we use content fingerprinting instead.

### Dry-Run Mode
- Added `--dry-run` flag to both commands
- Validates configuration without running full scan
- Shows: config loaded, Plex connection, available libraries, API key validity
- Useful for testing setup before long-running scans

### Summary Reports
- New summary display after each scan:
  - ComPlexionist banner
  - Report header with library name and scan date
  - Completion score (percentage of collection/episodes owned)
  - Stats: items analyzed, missing items, duration
  - Performance: Plex calls, TMDB/TVDB calls, cache hit rate
- Statistics tracking via new `ScanStatistics` class:
  - Tracks Plex API calls (libraries, movies, shows, episodes)
  - Tracks TMDB API calls (movie lookups, collection lookups)
  - Tracks TVDB API calls (series info, episode listings)
  - Tracks cache hits/misses for hit rate calculation
- Score calculation for both movies and TV
- Summary line format: `API calls: Plex: 2 | TMDB: 15 | Cache: 85% hit rate`

### Command Rename
- Renamed `episodes` command to `tv`
- More intuitive: "Movies or TV" mental model
- All internal references updated

### Banner Display
- ComPlexionist ASCII art banner shown consistently
- Displays on: main help, movies help, tv help, scan help
- Displays at start of movies/tv/scan commands
- Uses custom Click group/command classes for help integration

**Key files:**
- `src/complexionist/setup.py` - Setup wizard (new)
- `src/complexionist/validation.py` - Dry-run validation (new)
- `src/complexionist/statistics.py` - Statistics tracking (new)
- `src/complexionist/config.py` - INI format, search order
- `src/complexionist/cache.py` - Single-file cache, fingerprinting, batched saves
- `src/complexionist/cli.py` - New flags, summary reports, library selection
- `complexionist.ini.example` - Example configuration

---

## Phase 8: Consolidation (2025-01-26)

**Why:** Improve code architecture, reduce duplication, and optimize performance for long-term maintainability.

**What we did:**

### 8.1 CLI Output Consolidation
- Created `src/complexionist/output/` package with report formatters
- `ReportFormatter` base class with common methods:
  - `to_json()`, `to_csv()`, `to_text()`, `save_csv()`, `show_summary()`
- `MovieReportFormatter` for movie gap reports
- `TVReportFormatter` for TV episode gap reports
- Consolidates ~400 lines of output code from cli.py

### 8.2 CLI Command Consolidation
- Extracted `_create_progress_updater()` helper function
- Kept `movies()` and `tv()` commands separate (different options make shared executor complex)

### 8.3 API Client Base Class
- Created `src/complexionist/api/` package with shared utilities:
  - `base.py` - Unified exception hierarchy:
    - `APIError` - Base exception for all API errors
    - `APIAuthError` - Authentication failures (401)
    - `APINotFoundError` - Resource not found (404)
    - `APIRateLimitError` - Rate limited (429)
  - TMDB/TVDB exceptions inherit from both API base and their specific base
  - `helpers.py` - Common utilities:
    - `parse_date()` - ISO date string parsing
    - `cached_api_call()` - Cache check/store pattern

### 8.4 Model Mixins
- Created `src/complexionist/models/` package with reusable mixins:
  - `EpisodeCodeMixin` - Provides `episode_code` property (S01E05 format)
  - `DateAwareMixin` - Provides `is_date_past()` / `is_date_future()` helpers

### 8.5 Cache TTL Optimization
- Implemented conditional TTL based on collection membership:
  - Movies WITH collection: 30 days (collection membership rarely changes)
  - Movies WITHOUT collection: 7 days (might be added to a collection)
  - Collections: 30 days (new movies picked up via movie lookup)
- Reduces unnecessary API calls for stable data
- Edge case accepted: Movie added to new collection won't show for up to 7 days

### 8.6 Startup Performance
- Implemented lazy imports for faster startup:
  - Banner displays immediately on launch
  - "Starting up..." spinner while loading heavy modules (pydantic, httpx, plexapi)
  - Heavy modules loaded only when needed
- Fixes duplicate banner display in interactive mode
- Improves perceived startup time significantly for PyInstaller executables

**Key files:**
- `src/complexionist/api/__init__.py` - API package exports
- `src/complexionist/api/base.py` - Base exceptions
- `src/complexionist/api/helpers.py` - Shared utilities
- `src/complexionist/models/__init__.py` - Models package exports
- `src/complexionist/models/mixins.py` - Reusable mixins
- `src/complexionist/output/__init__.py` - Report formatters
- `src/complexionist/cache.py` - Updated TTL constants
- `src/complexionist/tmdb/client.py` - Conditional TTL logic
- `src/complexionist/cli.py` - Lazy imports, banner fixes

---

## Phase 8.5: MyPy Cleanup (2025-01-27)

**Why:** Make the MyPy CI job pass cleanly instead of being informational-only with errors.

**What we did:**

### Type Annotation Fixes
- Removed unused `type: ignore` comment in `plex/client.py`
- Added `cast()` for `response.json()` returns (returns `Any`) in:
  - `plex/client.py` (server name)
  - `cache.py` (cache get)
  - `tvdb/client.py` (API response)
  - `tmdb/client.py` (API response)
- Added return type annotations to `_parse_date()` methods

### Bug Fixes Discovered via Types
- Fixed `first_aired` → `firstAired` keyword argument when constructing `TVDBSeries` (mypy caught field alias mismatch)
- Fixed `cache.set()` in TVDB client passing `list[dict]` instead of `dict` - wrapped episodes list in `{"episodes": [...]}` structure
- Fixed `belongs_to_collection` passing raw dict instead of `TMDBCollectionInfo` object

**Key files:**
- `src/complexionist/plex/client.py` - Removed type ignore, added str cast
- `src/complexionist/cache.py` - Added cast for get() return
- `src/complexionist/tvdb/client.py` - Multiple fixes: cast, return types, field names, cache structure
- `src/complexionist/tmdb/client.py` - Cast, return types, TMDBCollectionInfo construction

---

## Phase 9a: Flet GUI (2025-01-28)

**Why:** Provide a user-friendly desktop GUI for users who prefer graphical interfaces over CLI.

**What we did:**

### Project Setup
- Added `flet>=0.25.0` to dependencies in `pyproject.toml`
- Created `src/complexionist/gui/` package with modular structure:
  - `app.py` - Main application entry point and scan execution
  - `state.py` - AppState dataclass for all UI state management
  - `theme.py` - Plex gold color scheme and theme configuration
  - `screens/` - Individual screen modules (base, dashboard, onboarding, results, scanning, settings)
- Added `--gui` and `--web` CLI flags to launch GUI mode

### Core Framework
- App shell with NavigationRail sidebar (Home, Results, Settings)
- Dark mode theme with Plex gold (#E5A00D) accent color
- Comprehensive state management via `AppState` dataclass:
  - Connection status tracking (Plex, TMDB, TVDB)
  - Scan progress with phase, current/total counts
  - Scan statistics (duration, API calls, cache metrics)
  - Report storage for results display

### Screens Implemented
- **Onboarding Wizard**: First-run setup detecting missing config, with back navigation from settings
- **Dashboard**: Connection status cards, scan type buttons (Movies, TV, Full Scan), settings access
- **Library Selection Dialog**: Dropdown selection for movie/TV libraries before scan
- **Scanning Screen**:
  - Pubsub-based progress updates from background thread
  - Live API stats display (Time, Plex calls, TMDB/TVDB calls, Cache hit rate)
  - Granular initialization phases (Loading cache, Connecting to Plex, etc.)
  - Cancel button with proper cleanup
- **Results Screen**:
  - Summary cards with scan statistics
  - ExpansionTile list for collections/shows
  - Owned movies shown with green checkmarks above "Missing X" header
  - Search filter for collection names and movie titles
  - Poster images with clickable TMDB links
  - Export menu (CSV, JSON, Clipboard)
- **Settings Screen**: Config path display, dark mode toggle, re-run setup option

### Technical Highlights
- **Thread-safe UI updates**: Background scan thread communicates via Flet's pubsub mechanism
- **Flet 0.80+ compatibility**: Updated APIs for dialogs, file pickers, window events
- **Async window close**: Proper handling of window close to avoid coroutine warnings
- **Export functionality**: FilePicker for CSV/JSON save, clipboard copy via `page.set_clipboard()`

### Gap Detection Integration
- `OwnedMovie` model added to track movies user owns in collections
- `owned_movie_list` field added to `CollectionGap` for results display
- `MovieGapFinder` populates owned movies when building gap reports
- Existing `MovieReportFormatter` and `TVReportFormatter` used for export

**Key files:**
- `src/complexionist/gui/app.py` - Main app, pubsub, scan execution (~500 lines)
- `src/complexionist/gui/state.py` - State management (~100 lines)
- `src/complexionist/gui/theme.py` - Theme configuration
- `src/complexionist/gui/screens/` - Screen modules:
  - `base.py` - BaseScreen class
  - `dashboard.py` - Dashboard with scan buttons
  - `onboarding.py` - First-run wizard
  - `results.py` - Results display with search/export (~560 lines)
  - `scanning.py` - Progress display (~175 lines)
  - `settings.py` - Settings panel
- `src/complexionist/gaps/models.py` - Added `OwnedMovie` class
- `src/complexionist/gaps/movies.py` - Populates `owned_movie_list`

**Known issues (to be fixed):**
- FilePicker `save_file()` may not trigger on some systems (Flet desktop bug)
- Web mode (`--web`) not yet implemented

---

## Phase 9a: GUI Polish (2025-01-29)

**Why:** Improve GUI stability, add user-friendly error handling, and prepare for future localization.

**What we did:**

### Centralized UI Strings
- Created `gui/strings.py` with all user-facing text:
  - Navigation labels, dashboard text, scan messages
  - Error messages for common failures (connection refused, unauthorized, rate limits)
  - Ready for future localization (i18n)

### Centralized Error Handling
- Created `gui/errors.py` with friendly error messaging:
  - `get_friendly_message(error)` - Converts technical exceptions to user-friendly text
  - `show_error()`, `show_warning()`, `show_success()`, `show_info()` - Snackbar helpers
  - Maps connection errors, API auth failures, rate limits to helpful messages

### Window State Persistence
- Created `gui/window_state.py`:
  - `WindowState` dataclass with width, height, x, y, maximized
  - `load_window_state()` / `save_window_state()` - Reads/writes to INI config [window] section
  - `validate_window_position()` - Ensures window stays on-screen
  - `apply_window_state()` / `capture_window_state()` - Flet page integration
- Window size and position saved on close, restored on startup

### Clean Window Close
- Fixed `ConnectionResetError` spam on Windows when closing the GUI
- Added `_SuppressingEventLoopPolicy` to suppress harmless asyncio errors
- Changed from `page.window.close()` to `page.window.destroy()` + `os._exit(0)` for clean exit

### Cache Display Format
- Updated scanning progress and results to show:
  `Time: 1m 32s | Plex 400 | TVDB 399 | Cache hits: 50%`
- Separated TMDB and TVDB cache stats properly
- Cache hit rate shows as green (>50%) or orange (<50%)

**Key files:**
- `src/complexionist/gui/strings.py` - UI strings (new)
- `src/complexionist/gui/errors.py` - Error handling (new)
- `src/complexionist/gui/window_state.py` - Window persistence (new)
- `src/complexionist/gui/app.py` - Window close handling, state integration
- `src/complexionist/gui/screens/scanning.py` - Updated stats display
- `src/complexionist/gui/screens/results.py` - Updated stats display

---

## Phase 9a.6: Code Consolidation (2025-01-29)

**Why:** Reduce duplication between CLI and GUI, improve maintainability, prepare for distribution.

**What we did:**

### Shared Modules Created
- **`constants.py`** - Centralized constants:
  - `PLEX_GOLD` / `PLEX_YELLOW` - Brand color constant
  - `SCORE_THRESHOLD_GOOD` (90%), `SCORE_THRESHOLD_WARNING` (70%)
  - `CACHE_HIT_RATE_GOOD` (50%)
  - `get_score_rating(score)` - Returns "good"/"warning"/"bad"

- **`errors.py`** - Shared error handling:
  - User-friendly error message constants
  - `get_friendly_message(error)` - Converts exceptions to friendly text
  - Used by both CLI and GUI

### Consolidations
- **ScanStats → ScanStatistics**: Removed duplicate `ScanStats` from `gui/state.py`, GUI now uses `ScanStatistics` directly
- **Duration formatting**: Added `duration_str` and `duration_seconds` properties to `ScanStatistics`
- **Config validation**: Added `has_valid_config()` to `config.py`
- **Connection testing**: Added `ConnectionTestResult` dataclass and `test_connections()` to `validation.py`

### New CLI Features
- **`--use-ignore-list`** flag for `movies`, `tv`, and `scan` commands
  - Uses ignored collection/show IDs from INI config (managed via GUI)
- **`--cli`** flag - Explicitly use CLI mode (GUI is now default)

### Distribution (PyInstaller)
- Updated `complexionist.spec` for Flet GUI bundling
- Single-file executable (57 MB) with all dependencies
- CLI and GUI both work from the same exe
- Default mode is GUI; use `--cli` for command-line mode

**Key files created/modified:**
- `src/complexionist/constants.py` - NEW: Shared constants
- `src/complexionist/errors.py` - NEW: Shared error messages
- `src/complexionist/validation.py` - Added `ConnectionTestResult`, `test_connections()`
- `src/complexionist/config.py` - Added `has_valid_config()`
- `src/complexionist/statistics.py` - Added `duration_str`, `duration_seconds`
- `src/complexionist/cli.py` - Added `--use-ignore-list`, `--cli` flags
- `src/complexionist/gui/state.py` - Removed `ScanStats`, uses `ScanStatistics`
- `src/complexionist/gui/errors.py` - Now imports from shared `errors.py`
- `complexionist.spec` - PyInstaller config for Flet GUI

---

## Folder Button Feature (2025-02-01)

**Why:** Allow users to quickly open the local folder containing their media files directly from the results screen.

**What we did:**

### Data Flow for File Paths
- Added `file_path` field to `PlexMovie` model
- Extract movie file paths in `PlexClient.get_movies()` (same pattern as episodes)
- Added `file_path` field to `OwnedMovie` model in gap reports
- Added `first_episode_path` field to `ShowGap` model
- Added computed `folder_path` properties to `CollectionGap` and `ShowGap`
- Pass file paths through both movie and episode gap finders

### UI Integration
- Added `open_folder()` utility function with cross-platform support:
  - Windows: `explorer.exe`
  - macOS: `open`
  - Linux: `xdg-open`
- Added "📁 Folder" button to TV show subtitle (before Geek link)
- Added "📁 Folder" button to movie collection subtitle (after "Missing X of Y")
- Folder button only appears when file path is available

**Key files:**
- `src/complexionist/plex/models.py` - Added `file_path` to `PlexMovie`
- `src/complexionist/plex/client.py` - Extract movie file paths
- `src/complexionist/gaps/models.py` - Added `file_path` to `OwnedMovie`, `first_episode_path` + `folder_path` to `ShowGap`, `folder_path` to `CollectionGap`
- `src/complexionist/gaps/movies.py` - Pass file paths through
- `src/complexionist/gaps/episodes.py` - Pass first episode path through
- `src/complexionist/gui/screens/results.py` - Added `open_folder()` and folder buttons

---

## Path Mapping for Network Access (2025-02-01)

**Why:** Plex server stores file paths relative to its own filesystem (e.g., `\volume1\video\...`), which may not match the network paths accessible from a client machine (e.g., `\\Storage4\video\...`). This prevents the folder button from opening the correct location.

**What we did:**

### Configuration Support
- Added `PathsConfig` model with `plex_prefix` and `local_prefix` fields
- Added `[paths]` section parsing in config loading
- Added `map_plex_path()` function to transform Plex server paths to local network paths
- Path normalization handles backslash escaping differences between INI files and actual paths

### Settings UI
- Added "Path Mapping" section to Settings screen
- Text fields for Plex server path prefix and local network path prefix
- Save button persists settings to INI config file

### How It Works
1. User configures path mapping in Settings (or manually in INI file):
   - `plex_prefix = \volume1\video` (single leading backslash for Plex path)
   - `local_prefix = \\Storage4\video` (double backslash for UNC network path)
2. When folder button is clicked, `open_folder()` calls `map_plex_path()`
3. The Plex path prefix is replaced with the local prefix
4. `os.startfile()` (Windows) opens the mapped path in Explorer

**Key files:**
- `src/complexionist/config.py` - Added `PathsConfig`, `map_plex_path()`, `[paths]` section parsing
- `src/complexionist/gui/screens/settings.py` - Added Path Mapping UI section
- `src/complexionist/gui/screens/results.py` - `open_folder()` applies path mapping
- `complexionist.ini.example` - Added `[paths]` section documentation

---

## Collection Folder Organization Feature (2026-02-02)

**Why:** When movies from a collection are scattered across different folders in the library, it's hard to keep them organized. Users wanted a way to consolidate movies from the same collection into a dedicated collection folder.

**What we did:**

### Organize Button
- Added "🎬 Organize" button to movie collection results (orange, appears when movies need organizing)
- Button appears when owned movies are NOT in a folder named after the collection
- Clicking opens a dialog with current locations and target folder

### Organize Dialog
- Shows each movie file with its current location
- Indicates which files will be moved (→ arrow) vs already organized (✓ checkmark)
- Displays the target collection folder path (e.g., `\\Storage4\video\Movies\Alien`)
- Shows count of files that will be moved

### Safety Checks
Before enabling the "Move Files" button, the feature checks:
1. Library folder exists and is writable
2. Collection folder (if exists) is writable
3. Source files exist
4. No duplicate filenames among movies being moved
5. No files with same name already exist in target folder

If any check fails, the button is disabled with a tooltip explaining why.

### Move Operation
- Creates collection folder if it doesn't exist
- Moves each movie **file** directly into the collection folder
- Shows success/error snackbar with count of files moved

### Library Locations from Plex API
- Added `locations` field to `PlexLibrary` model
- Updated `PlexClient.get_libraries()` to fetch library folder paths
- Collection folder target now uses Plex API locations (preferred) with path mapping applied
- Falls back to deriving from file paths if locations unavailable

**Key files:**
- `src/complexionist/gui/screens/results.py` - Organize button, dialog, safety checks, move operation
- `src/complexionist/gaps/models.py` - Added `expected_folder_name`, `needs_organizing`, `collection_folder_target`, `library_locations`
- `src/complexionist/gaps/movies.py` - Pass library locations through to CollectionGap
- `src/complexionist/plex/models.py` - Added `locations` to PlexLibrary
- `src/complexionist/plex/client.py` - Fetch library locations from Plex API

---

## TV Show Status Indicator (2026-02-10)

**Why:** Users couldn't tell at a glance whether a show was still airing or had ended, which is useful context when deciding whether to pursue missing episodes.

**What we did:**
- Added show status (Continuing, Ended, etc.) to TV scan results display
- Status shown as a colored chip next to the show title
- Improved scanning UX with better progress messaging

**Key files:**
- `src/complexionist/gui/screens/results.py` - Status chip in TV results
- `src/complexionist/gui/screens/dashboard.py` - Scanning UX improvements

---

## Conditional Cache TTLs for Ended Shows (2026-02-10)

**Why:** Shows that have ended or been cancelled won't get new episodes, so we can safely cache their data for much longer, dramatically reducing API calls for subsequent scans.

**What we did:**
- TVDB episodes for ended shows: 1-year TTL (vs 24h for continuing shows)
- TVDB series info for ended shows: 1-year TTL (vs 7 days for continuing)
- Added `_is_ended_status()` helper to check show status
- Added `series_status` parameter to `get_series_episodes()` for conditional TTL
- Reordered API calls in episode gap finder to fetch series info before episodes (need status for cache TTL)

**Key files:**
- `src/complexionist/cache.py` - New TTL constants (`TVDB_SERIES_ENDED_TTL_HOURS`, `TVDB_EPISODES_ENDED_TTL_HOURS`)
- `src/complexionist/tvdb/client.py` - Conditional TTL logic, `_is_ended_status()` helper
- `src/complexionist/gaps/episodes.py` - Reordered calls, thread `series_status` through

---

## Code Review & Robustness Improvements (2026-02-10)

**Why:** Comprehensive code review identified 11 findings across stability, code reuse, efficiency, and dependencies. Addressed 9 of 11 (one deferred, one informational).

**What we did:**

### Thread-Safe Cache (Review #1)
- Added `threading.RLock` to `Cache` class
- Wrapped all public methods (`get`, `set`, `delete`, `clear`, `flush`, `stats`, etc.) with lock
- Split `stats()` into public (holds lock) and `_stats_unlocked()` (internal)

### YAML Config Error Handling (Review #2)
- Wrapped `_load_yaml_config()` in try/except for `yaml.YAMLError` and `OSError`
- Graceful fallback to empty config instead of crash

### Results Screen Shared Builders (Review #4)
- Extracted 7 shared methods to reduce movie/TV UI duplication:
  - `_build_summary_card()`, `_build_results_column()`, `_build_content_with_poster()`
  - `_build_ignore_trailing()`, `_build_empty_state()`, `_build_no_matches()`, `_build_title_button()`

### BaseAPIClient Extraction (Review #5)
- Created `BaseAPIClient` in `api/base.py` with shared patterns:
  - `_handle_response()`, `_parse_date()`, `close()`, context manager
  - `_on_auth_failure()` hook for TVDB token refresh
  - `_record_cache_hit()` / `_record_cache_miss()` for stats
  - Class attributes for error types, message key, API name
- TMDB and TVDB clients now inherit from `BaseAPIClient`

### Idle-Time Cache Pruning (Review #7)
- Added `cache.cleanup_expired()` call after scan completes
- Runs during idle time (after scan), not at startup

### Atomic Cache Saves (Review #8)
- Rewrote `_save()` to write to `.tmp` file first, then rename
- Fallback to direct write on `OSError`

### Build Optimizations (Review #9)
- Excluded pygments, numpy, pandas, matplotlib, scipy, PIL, tkinter, pytest from exe
- Reduced exe from ~92MB to ~55MB
- Robust spec file with dynamic package finding via `importlib`
- Flet desktop runtime properly bundled (all plugins required)

### Dependency Updates (Review #10, #11)
- Tightened pytest-asyncio pin from `>=0.23.0` to `>=0.26.0`
- Validated plexapi 4.18.0 compatibility (all stable API usage confirmed)

**Key files:**
- `src/complexionist/cache.py` - Thread safety, atomic save, cleanup
- `src/complexionist/config.py` - YAML error handling
- `src/complexionist/gui/screens/results.py` - Shared builders
- `src/complexionist/api/base.py` - BaseAPIClient class
- `src/complexionist/api/__init__.py` - Export BaseAPIClient
- `src/complexionist/tmdb/client.py` - Inherit BaseAPIClient
- `src/complexionist/tvdb/client.py` - Inherit BaseAPIClient
- `src/complexionist/gui/app.py` - Idle-time cache pruning
- `complexionist.spec` - Optimized build config
- `pyproject.toml` - pytest-asyncio pin
- `docs/code review 1.md` - Full review document

---

## Multi Plex Server Support (2026-02-19)

**Why:** Users with multiple Plex servers (e.g. main + 4K, living room + bedroom) had to manually edit the INI file to switch between servers. This adds first-class support for configuring and managing multiple servers, selecting which one to scan against.

**What we did:**

### Config Model
- Added `PlexServerConfig` Pydantic model with `name`, `url`, `token` fields
- Changed `PlexConfig` to hold `servers: list[PlexServerConfig]` with backward-compat `url`/`token` properties
- INI format uses indexed sections: `[plex:0]`, `[plex:1]`, etc.
- Old `[plex]` section auto-migrates to `[plex:0]` on load (fully backward-compatible)
- Added `get_plex_server(index)` and `save_plex_servers(servers)` helper functions
- Updated `save_default_config()` to write `[plex:0]` format with auto-detected server name

### GUI - Server Management (Settings)
- New "Plex Servers" section in Settings with server list
- Status dots (green = connected, grey = not tested) per server
- Edit (pencil) and Delete (X) buttons per server row
- Add/edit form with URL, Token, and optional Name fields
- "Test & Save" button validates connection in background, auto-fills name from Plex `friendlyName`
- Delete confirmation dialog

### GUI - Server Selection (Scan Dialog)
- Server dropdown in scan dialog (only shown when 2+ servers configured)
- Changing server refreshes movie/TV library dropdowns for that server
- Active server persisted in library state

### GUI - Dashboard
- Shows server count in connection status when multiple servers configured

### CLI
- Added `--server` / `-s` flag to `movies`, `tv`, and `scan` commands
- Resolves by name (case-insensitive) or index
- Updated `config show` to display all servers with indices

### Supporting Changes
- `LibrarySelection` dataclass: added `active_server: int = 0` field
- `AppState`: added `plex_servers` list and `active_server_index`
- `validation.py`: added `test_plex_server(url, token)` function, updated `test_connections()` with optional URL/token overrides
- Onboarding: saves as `[plex:0]` format, captures `friendlyName`
- New file: `src/complexionist/gui/library_state.py` for library selection persistence

**Key files:**
- `src/complexionist/config.py` - Multi-server config model and INI persistence
- `src/complexionist/gui/screens/settings.py` - Server management UI
- `src/complexionist/gui/app.py` - Scan dialog server selector
- `src/complexionist/gui/library_state.py` - Library + server selection persistence (new)
- `src/complexionist/cli.py` - `--server` flag and server resolution
- `src/complexionist/validation.py` - Individual server testing
- `src/complexionist/gui/screens/onboarding.py` - Saves as `[plex:0]`
- `src/complexionist/gui/screens/dashboard.py` - Server count display
- `src/complexionist/gui/state.py` - Server state fields

---

## Current Status

**Version:** 2.0.128 (Flet 0.83 upgrade, all dependencies current)

**All core features complete.** See `TODO.md` for remaining enhancements.
