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

### F3: Caching (Optional Enhancement)

**Description:** Cache API responses to reduce redundant calls on subsequent runs.

**Rationale:**
- TMDB/TVDB rate limits
- Faster subsequent runs
- Reduced API load

**Cache Strategy:**
| Data Type | TTL | Rationale |
|-----------|-----|-----------|
| TMDB movie details | 7 days | Rarely changes |
| TMDB collection | 7 days | New movies are rare |
| TVDB episode list | 24 hours | Episodes can be added |
| Plex library scan | No cache | Always fresh |

**Implementation:**
- Store in `~/.complexionist/cache/` or configurable location
- SQLite database or JSON files
- `--no-cache` flag to force fresh data
- `--clear-cache` command to purge

---

## Configuration

### Required Credentials
| Credential | Source | Storage |
|------------|--------|---------|
| Plex Token | User provides or login flow | `.env` file |
| Plex Server URL | User provides | `.env` or config |
| TMDB API Key | User registers at themoviedb.org | `.env` file |
| TVDB API Key | User registers at thetvdb.com | `.env` file |

### Config File (optional)
Location: `~/.complexionist/config.yaml` or `./config.yaml`

```yaml
plex:
  url: "http://192.168.1.100:32400"
  token: "${PLEX_TOKEN}"  # or direct value

tmdb:
  api_key: "${TMDB_API_KEY}"

tvdb:
  api_key: "${TVDB_API_KEY}"
  pin: ""  # optional subscriber PIN

options:
  exclude_future: true
  exclude_specials: true
  recent_threshold_hours: 24
  min_collection_size: 2

exclusions:
  shows:
    - "Talk Show Name"
    - "Daily News Show"
```

---

## CLI Interface

### Commands

```bash
# Scan movie library for collection gaps
complexionist movies [--library "Movies"] [--no-cache]

# Scan TV library for episode gaps
complexionist episodes [--library "TV Shows"] [--no-cache]

# Scan both
complexionist scan [--no-cache]

# Configuration
complexionist config --show
complexionist config --set plex.url "http://..."
complexionist cache --clear

# Authentication helpers
complexionist auth plex --login
complexionist auth plex --token "YOUR_TOKEN"
complexionist auth tmdb --key "YOUR_KEY"
complexionist auth tvdb --key "YOUR_KEY"
```

### Output Options

```bash
# Output formats
--format text      # Human-readable (default)
--format json      # Machine-readable
--format csv       # Spreadsheet-friendly

# Verbosity
-v, --verbose      # Show progress and details
-q, --quiet        # Only show results

# Filtering (override config)
--include-future   # Include unreleased content
--include-specials # Include Season 0
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

### v1.0 (MVP)
- [ ] Connect to Plex and authenticate
- [ ] Scan movie library and detect collection gaps
- [ ] Scan TV library and detect episode gaps
- [ ] Exclude future releases (default on)
- [ ] CLI with text output
- [ ] Basic error handling

### v1.1
- [ ] Caching for API responses
- [ ] JSON/CSV output formats
- [ ] Configuration file support
- [ ] Show exclusion list

### v2.0
- [ ] GUI application
