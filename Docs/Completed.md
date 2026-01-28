# ComPlexionist - Completed Work

This file is a durable record of finished work. Each entry captures what shipped, why it mattered, and where it lives.

See `TODO.md` for forward-looking work items.

---

## Project Setup and Documentation (2025-01-24)

**Why:** Establish project foundation with research and documentation before implementation.

**What we did:**
- Created `README.md` with project overview and feature descriptions
- Created `Docs/Plex-Background.md` with comprehensive Plex API research:
  - Authentication methods (X-Plex-Token, JWT, PIN flow)
  - Library architecture and content separation
  - Collections API and the "missing movies" problem
  - TV show hierarchy (Show > Season > Episode)
  - External data sources (TMDB for movies, TVDB for TV)
  - python-plexapi library overview
- Created `Docs/TODO.md` with development task breakdown
- Adapted `agents.md` from TVRenamer project for ComPlexionist workflow

**Key files:**
- `README.md`
- `Docs/Plex-Background.md`
- `Docs/TODO.md`
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
- `Docs/Reference-Analysis.md`

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
- `Docs/Specification.md`
- `Docs/Implementation-Plan.md`

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

## Phase 9a: Flet GUI (2025-01-28) - IN PROGRESS

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

## Current Status

**Version:** 2.0.x (Phase 9a in progress)

**Features complete:**
- Movie collection gap detection with TMDB
- TV episode gap detection with TVDB
- Multi-episode filename parsing (S01E01-02 variants)
- Caching with fingerprint-based invalidation
- First-run setup wizard with live validation
- Library selection (`--library` flag)
- Collection filtering (`--min-owned` flag)
- Summary reports with completion score, API stats, cache metrics
- Dry-run validation mode (`--dry-run` flag)
- Auto-CSV output with `--no-csv` option
- INI configuration format with fallback support
- Conditional cache TTL for optimized API usage
- Fast startup with lazy module loading
- Clean MyPy type checking (no errors)
- **NEW: Desktop GUI with Flet framework**
  - Dashboard with connection status
  - Scanning with live progress
  - Results with search and export
  - Settings panel

**Next:** Phase 9a polish (error handling, keyboard shortcuts) and Phase 9b (browser extension)
