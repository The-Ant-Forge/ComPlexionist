# ComPlexionist - Project Specification

## Overview

ComPlexionist is a tool that identifies missing content in Plex Media Server libraries:
1. **Movie Collection Gaps:** Missing movies from collections you've started
2. **TV Episode Gaps:** Missing episodes from TV series you own

The tool compares your Plex library against authoritative external databases (TMDB, TVDB) to identify gaps.

---

## Goals

- **Primary:** Help users discover what content they're missing
- **Non-goal:** Automated downloading or acquisition of content
- **Non-goal:** Modifying Plex library or metadata

---

## Tech Stack

| Component | Choice | Rationale |
|-----------|--------|-----------|
| Language | Python 3.11+ | Mature ecosystem, python-plexapi library |
| Plex Integration | python-plexapi | Well-maintained, feature-complete |
| Movie Data | TMDB API | Has collection membership data |
| TV Data | TVDB v4 API | Comprehensive episode listings |
| CLI Framework | Click or Typer | Modern Python CLI tools |
| GUI (future) | TBD | Consider: PyQt, Electron, or web-based |
| Caching | SQLite or JSON files | Simple, no external dependencies |

---

## Features

### F1: Movie Collection Gaps

**Description:** Identify movies missing from collections in your Plex movie library.

**User Story:** As a user, I want to see which movies I'm missing from collections I've started (e.g., I have Alien but not Aliens), so I can discover related content.

**Workflow:**
1. Connect to Plex server
2. Scan movie library for all movies
3. For each movie with a TMDB ID:
   - Query TMDB for movie details
   - If movie belongs to a collection, fetch full collection
4. Compare collection movies against Plex library (by TMDB ID)
5. Report missing movies, grouped by collection

**Filtering:**
- **Exclude future releases:** Movies with release date > today (configurable)
- **Minimum collection size:** Only report collections with N+ movies (default: 2)

**Output:**
```
Alien Collection (missing 2 of 6):
  - Alien³ (1992)
  - Alien Resurrection (1997)

Terminator Collection (missing 1 of 6):
  - Terminator: Dark Fate (2019)
```

---

### F2: TV Episode Gaps

**Description:** Identify missing episodes from TV series in your Plex TV library.

**User Story:** As a user, I want to see which episodes I'm missing from shows I'm collecting, so I can complete my library.

**Workflow:**
1. Connect to Plex server
2. Scan TV library for all shows
3. For each show with a TVDB GUID:
   - Query TVDB for all episodes
   - Filter episodes (see below)
4. Compare TVDB episodes against Plex episodes
5. Report missing episodes, grouped by show and season

**Filtering:**
- **Exclude future episodes:** Episodes with air date > today (configurable)
- **Exclude specials:** Season 0 episodes (configurable, default: exclude)
- **Exclude very recent:** Episodes aired within N hours (configurable, default: 24h)
- **Show exclusion list:** User-defined list of shows to skip

**Multi-Episode File Handling:**
- Parse filenames for episode ranges (e.g., `S02E01-02`, `S02E01-E02`)
- Don't flag episodes that are part of a combined file

**Output:**
```
Breaking Bad (missing 3 episodes):
  Season 2:
    - S02E05 - Breakage
    - S02E06 - Peekaboo
  Season 4:
    - S04E11 - Crawl Space

The Office (US) (missing 12 episodes):
  Season 3:
    - S03E01 - Gay Witch Hunt
    - S03E02 - The Convention
    ... and 10 more
```

---

### F3: Caching

**Description:** Cache API responses to reduce redundant calls on subsequent runs.

**Rationale:**
- TMDB/TVDB rate limits
- Faster subsequent runs
- Reduced API load

**Cache Strategy:**
| Data Type | Invalidation | Rationale |
|-----------|--------------|-----------|
| TMDB movie details | Plex library update | Only re-fetch when library changes |
| TMDB collection | Plex library update | Only re-fetch when library changes |
| TVDB episode list | Plex library update | Only re-fetch when library changes |
| Plex library scan | Never cached | Always fresh |

**Implementation (v1.2):**
- Single JSON file: `complexionist.cache.json` next to config
- Structure organized by library name
- Fingerprint-based invalidation (item count + ID hash)
- `cache clear` command to purge all cached data
- `cache refresh` command to invalidate fingerprints
- Cache is always enabled (no opt-out needed)

**Note:** Plex doesn't expose library `updatedAt` via API, so we use content fingerprinting instead.

---

## Configuration

### Required Credentials
| Credential | Source | Storage |
|------------|--------|---------|
| Plex Token | User provides or login flow | `complexionist.ini` |
| Plex Server URL | User provides | `complexionist.ini` |
| TMDB API Key | User registers at themoviedb.org | `complexionist.ini` |
| TVDB API Key | User registers at thetvdb.com | `complexionist.ini` |

### Config File
Location search order (v1.2+):
1. Same directory as executable
2. Current working directory
3. User home directory

**Format: `complexionist.ini` (INI style)**
```ini
[plex]
url = http://192.168.1.100:32400
token = YOUR_PLEX_TOKEN

[tmdb]
api_key = YOUR_TMDB_API_KEY

[tvdb]
api_key = YOUR_TVDB_API_KEY

[options]
exclude_future = true
exclude_specials = true
recent_threshold_hours = 24
min_collection_size = 2
min_owned = 2

[exclusions]
shows = Talk Show Name, Daily News Show
collections = Some Collection Name
```

### First-Run Experience (v1.2+)
When no config file is found:
1. Display welcome message
2. Prompt for Plex URL and token
3. Prompt for TMDB API key
4. Prompt for TVDB API key
5. Save to `complexionist.ini` in current directory
6. Offer to run `--dry-run` to validate setup

### Fallback Support
For backwards compatibility, `.env` files are still read if `complexionist.ini` is not found.

---

## CLI Interface

### Commands

```bash
# Scan movie library for collection gaps
complexionist movies [--library "Movies"] [--dry-run]

# Scan TV library for episode gaps
complexionist tv [--library "TV Shows"] [--dry-run]

# Scan both
complexionist scan [--dry-run]

# Configuration
complexionist config show      # Display current configuration
complexionist config path      # Show config file locations
complexionist config setup     # Run interactive setup wizard

# Cache management
complexionist cache clear      # Clear all cached data
complexionist cache stats      # Show cache statistics
complexionist cache refresh    # Invalidate fingerprints for re-fetch
```

### Output Options

```bash
# Output formats
--format text      # Human-readable (default)
--format json      # Machine-readable
--format csv       # Spreadsheet-friendly

# CSV output (v1.2+)
# Automatic: {Library}_gaps_{date}.csv saved to working directory
--no-csv           # Disable automatic CSV output

# Verbosity
-v, --verbose      # Show progress and details
-q, --quiet        # Only show results

# Filtering (override config)
--include-future   # Include unreleased content
--include-specials # Include Season 0
--min-owned N      # Minimum owned movies to report collection (default: 2)

# Library selection (v1.2+)
--library "Name"   # Scan specific library
                   # If not specified, lists available libraries

# Validation
--dry-run          # Validate config without making API calls (v1.2+)
```

---

## Data Flow

### Movie Collection Gaps

```
┌─────────────┐     ┌─────────────┐     ┌─────────────┐
│    Plex     │────▶│ ComPlexion- │────▶│   Report    │
│   Movies    │     │    ist      │     │  (Missing)  │
└─────────────┘     └──────┬──────┘     └─────────────┘
                          │
                          ▼
                   ┌─────────────┐
                   │    TMDB     │
                   │ Collections │
                   └─────────────┘
```

1. Fetch all movies from Plex with TMDB IDs
2. Build set of owned TMDB IDs
3. For each movie, query TMDB for collection membership
4. For each unique collection, fetch full movie list
5. Diff: Collection movies - Owned movies = Missing

### TV Episode Gaps

```
┌─────────────┐     ┌─────────────┐     ┌─────────────┐
│    Plex     │────▶│ ComPlexion- │────▶│   Report    │
│  TV Shows   │     │    ist      │     │  (Missing)  │
└─────────────┘     └──────┬──────┘     └─────────────┘
                          │
                          ▼
                   ┌─────────────┐
                   │    TVDB     │
                   │  Episodes   │
                   └─────────────┘
```

1. Fetch all shows from Plex with TVDB GUIDs
2. For each show, build map of owned episodes: `{season: [episodes]}`
3. Query TVDB for complete episode list
4. Filter: Remove future, specials (if configured), very recent
5. Diff: TVDB episodes - Owned episodes = Missing

---

## Error Handling

| Scenario | Handling |
|----------|----------|
| Plex connection failed | Clear error message, suggest checking URL/token |
| TMDB/TVDB rate limited | Exponential backoff, respect Retry-After |
| Movie has no TMDB ID | Skip, optionally warn in verbose mode |
| Show has no TVDB GUID | Skip, optionally warn in verbose mode |
| Collection not found on TMDB | Skip, log warning |
| Show not found on TVDB | Skip, log warning |

---

## Future Enhancements (Out of Scope for v1)

- **GUI:** Desktop or web-based interface
- **Notifications:** Alert when new movies added to collections
- **Watchlist integration:** Suggest missing content based on watchlists
- **Multiple servers:** Support scanning multiple Plex servers
- **Radarr/Sonarr integration:** Add missing content to download queues
- **TMDB for TV:** Alternative to TVDB for episode data

---

## Project Structure (Proposed)

```
complexionist/
├── src/
│   └── complexionist/
│       ├── __init__.py
│       ├── cli.py              # CLI entry point
│       ├── config.py           # Configuration handling
│       ├── cache.py            # Caching logic
│       ├── plex/
│       │   ├── __init__.py
│       │   ├── client.py       # Plex connection
│       │   ├── movies.py       # Movie library scanning
│       │   └── shows.py        # TV library scanning
│       ├── tmdb/
│       │   ├── __init__.py
│       │   └── client.py       # TMDB API client
│       ├── tvdb/
│       │   ├── __init__.py
│       │   └── client.py       # TVDB API client
│       ├── gaps/
│       │   ├── __init__.py
│       │   ├── movies.py       # Movie gap detection
│       │   └── episodes.py     # Episode gap detection
│       └── output/
│           ├── __init__.py
│           ├── text.py         # Text formatter
│           ├── json.py         # JSON formatter
│           └── csv.py          # CSV formatter
├── tests/
│   ├── __init__.py
│   ├── test_plex.py
│   ├── test_tmdb.py
│   ├── test_tvdb.py
│   └── test_gaps.py
├── Docs/
│   └── ...
├── pyproject.toml              # Project config (poetry/pip)
├── README.md
└── .env.example
```

---

## Success Criteria

### v1.0 (MVP) ✓
- [x] Connect to Plex and authenticate
- [x] Scan movie library and detect collection gaps
- [x] Scan TV library and detect episode gaps
- [x] Exclude future releases (default on)
- [x] CLI with text output
- [x] Basic error handling

### v1.1 ✓
- [x] Caching for API responses
- [x] JSON/CSV output formats
- [x] Configuration file support
- [x] Show exclusion list
- [x] CI/CD with GitHub Actions
- [x] Windows executable builds

### v1.2 ✓
- [x] First-run interactive setup wizard with live validation
- [x] `complexionist.ini` config format (INI)
- [x] Library selection (`--library`)
- [x] Automatic CSV output with library name
- [x] `--dry-run` mode for config validation
- [x] Collection filtering (`--min-owned`)
- [x] Portable cache (single JSON file next to config)
- [x] Summary with completion score, timing, and API stats
- [x] Command rename: `episodes` → `tv`

### v2.0
- [ ] GUI application

---

## Implementation Notes

**Current implementation status (v1.2 - Phase 7.6 complete):**

1. **Project Structure:**
   - Plex: `client.py` + `models.py` (consolidated)
   - Output: Formatting built into `cli.py`
   - TMDB: `client.py` + `models.py` with cache support
   - TVDB: `client.py` + `models.py` with cache support
   - Gaps: `movies.py` + `episodes.py` + `models.py`
   - Config: `config.py` for INI configuration
   - Cache: `cache.py` for single-file JSON caching
   - Setup: `setup.py` for first-run wizard
   - Validation: `validation.py` for dry-run mode
   - Statistics: `statistics.py` for scan metrics
   - Version: `_version.py` for dynamic versioning

2. **CLI Commands Implemented:**
   - `movies` - Find missing movies from collections
   - `tv` - Find missing TV episodes (renamed from `episodes`)
   - `scan` - Run both movies and TV scans
   - `config show` - Display current configuration
   - `config path` - Show configuration file paths
   - `config setup` - Run interactive setup wizard
   - `cache clear` - Clear cached API responses
   - `cache stats` - Display cache statistics
   - `cache refresh` - Invalidate fingerprints

3. **CLI Options Implemented:**
   - `--verbose` / `-v` - Detailed output
   - `--quiet` / `-q` - Minimal output (no progress)
   - `--library` / `-l` - Select specific library
   - `--dry-run` - Validate config without scanning
   - `--no-csv` - Disable automatic CSV output
   - `--min-owned` - Minimum owned movies for collection filter
   - `--include-future` - Include unreleased content
   - `--include-specials` - Include Season 0
   - `--min-collection-size` - Filter small collections
   - `--recent-threshold` - Skip recently aired episodes
   - `--exclude-show` - Exclude specific shows
   - `--format` / `-f` - Output format (text/json/csv)

4. **Caching Implementation (v1.2):**
   - Single JSON file: `complexionist.cache.json` next to config
   - Fingerprint-based invalidation (item count + ID hash)
   - Batched saves (every 250 changes) for Windows compatibility
   - TMDB movies/collections: 7-day TTL
   - TVDB episodes: 24-hour TTL
   - Portable: no files scattered in hidden directories

5. **Versioning & CI/CD:**
   - Version format: `MAJOR.MINOR.{commit_count}` (e.g., 1.2.47)
   - Base version in `_version.py`, commit count auto-calculated
   - GitHub Actions CI: tests + lint on push/PR
   - GitHub Actions Build: Windows executable on version tags
