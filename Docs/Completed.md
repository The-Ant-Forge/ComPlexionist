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

## Current Status

**Tests:** 72 total, all passing
- CLI: 6 tests
- Plex: 17 tests
- TMDB: 14 tests
- Gaps: 15 tests
- TVDB: 20 tests

**Next:** Phase 5 (Episode Gap Detection) - Wire Plex + TVDB together to find missing episodes
