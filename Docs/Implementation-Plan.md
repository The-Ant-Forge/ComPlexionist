# ComPlexionist - Implementation Plan

This document outlines the phased approach to building ComPlexionist.

---

## Phase 0: Project Setup

**Goal:** Establish Python project structure and development environment.

### Tasks

1. **Initialize Python project**
   - Create `pyproject.toml` with dependencies
   - Set up virtual environment
   - Configure VS Code / IDE settings

2. **Define dependencies**
   ```
   plexapi           # Plex integration
   httpx             # Async HTTP client (TMDB/TVDB)
   click or typer    # CLI framework
   python-dotenv     # Environment variables
   pydantic          # Data validation/models
   rich              # Pretty terminal output
   pytest            # Testing
   ```

3. **Create project structure**
   - `src/complexionist/` package
   - `tests/` directory
   - `.env.example` template

4. **Set up tooling**
   - Ruff (linting/formatting)
   - pytest configuration
   - GitHub Actions workflow (later)

**Deliverable:** Empty but runnable Python project with `complexionist --help` working.

---

## Phase 1: Plex Integration

**Goal:** Connect to Plex and extract library data.

### Tasks

1. **Plex authentication**
   - Support direct token via environment variable
   - Support username/password login flow (optional)
   - Validate connection on startup

2. **Library scanning**
   - List available libraries
   - Identify movie vs TV libraries by type

3. **Movie data extraction**
   - Fetch all movies from library
   - Extract: title, year, TMDB ID (from GUIDs)
   - Handle movies without TMDB ID

4. **TV show data extraction**
   - Fetch all shows from library
   - Extract: title, year, TVDB GUID
   - Fetch all episodes per show
   - Extract: season number, episode number, title, filename
   - Handle shows without TVDB GUID

**Deliverable:** CLI commands that list Plex movies and shows with their external IDs.

```bash
complexionist plex movies --library "Movies"
complexionist plex shows --library "TV Shows"
```

---

## Phase 2: TMDB Integration (Movie Collections)

**Goal:** Query TMDB for collection data.

### Tasks

1. **TMDB client**
   - Authenticate with API key
   - Implement rate limiting / backoff

2. **Movie details endpoint**
   - `GET /movie/{id}` → extract `belongs_to_collection`
   - Return collection ID and name if present

3. **Collection endpoint**
   - `GET /collection/{id}` → get all movies in collection
   - Extract: movie ID, title, release date

4. **Data models**
   ```python
   class TMDBMovie:
       id: int
       title: str
       release_date: date | None

   class TMDBCollection:
       id: int
       name: str
       movies: list[TMDBMovie]
   ```

**Deliverable:** CLI command to look up a collection by movie ID.

```bash
complexionist tmdb collection --movie-id 348
# Returns: "Alien Collection" with 6 movies
```

---

## Phase 3: Movie Gap Detection

**Goal:** Compare Plex movies against TMDB collections to find gaps.

### Tasks

1. **Build owned movie set**
   - Scan Plex movies
   - Create set of owned TMDB IDs

2. **Discover collections**
   - For each owned movie, query TMDB for collection membership
   - Deduplicate collections (many movies may share same collection)

3. **Fetch full collections**
   - For each unique collection, get all movies

4. **Filter and compare**
   - Filter out future releases (release_date > today)
   - Filter out collections with < min_size movies
   - Diff: collection movies - owned = missing

5. **Generate report**
   - Group by collection
   - Sort by collection name
   - Show release year for each missing movie

**Deliverable:** Working movie gaps feature.

```bash
complexionist movies --library "Movies"
```

---

## Phase 4: TVDB Integration (TV Episodes)

**Goal:** Query TVDB for episode data.

### Tasks

1. **TVDB v4 client**
   - Login with API key → Bearer token
   - Handle token refresh
   - Implement rate limiting

2. **Series episodes endpoint**
   - `GET /series/{id}/episodes/default` (paginated)
   - Handle pagination
   - Extract: season, episode number, name, air date

3. **Data models**
   ```python
   class TVDBEpisode:
       season: int
       episode: int
       name: str
       air_date: date | None

   class TVDBSeries:
       id: int
       name: str
       episodes: list[TVDBEpisode]
   ```

**Deliverable:** CLI command to look up episodes by TVDB ID.

```bash
complexionist tvdb episodes --series-id 81189
# Returns: Breaking Bad with all episodes
```

---

## Phase 5: Episode Gap Detection

**Goal:** Compare Plex episodes against TVDB to find gaps.

### Tasks

1. **Build owned episode map**
   - Scan Plex shows
   - For each show: `{season: {episode_num: episode_title}}`

2. **Multi-episode file handling**
   - Parse filenames for ranges (`S02E01-02`)
   - Expand to individual episode numbers
   - Mark all as owned

3. **Fetch TVDB episodes**
   - For each show with TVDB GUID, fetch episode list

4. **Filter episodes**
   - Exclude Season 0 (specials) if configured
   - Exclude air_date > today (future)
   - Exclude air_date < 24 hours ago (very recent)

5. **Compare and find gaps**
   - For each TVDB episode, check if owned
   - Match by season + episode number
   - Fallback: match by name (for edge cases)

6. **Generate report**
   - Group by show, then season
   - Truncate long lists (show first 3 + last 3)

**Deliverable:** Working episode gaps feature.

```bash
complexionist episodes --library "TV Shows"
```

---

## Phase 6: CLI Polish & Output Formats

**Goal:** Production-ready CLI with multiple output formats.

### Tasks

1. **Unified scan command**
   ```bash
   complexionist scan  # Both movies and episodes
   ```

2. **Output formats**
   - Text (default, human-readable)
   - JSON (machine-readable)
   - CSV (spreadsheet import)

3. **Progress indicators**
   - Show scanning progress with `rich`
   - Verbose mode for debugging

4. **Error handling polish**
   - Clear error messages
   - Suggestions for common issues
   - Exit codes for scripting

5. **Configuration**
   - `.env` file support
   - Optional YAML config file
   - CLI flags override config

**Deliverable:** Polished v1.0 CLI.

---

## Phase 7: Caching (v1.1)

**Goal:** Reduce API calls on repeated runs.

### Tasks

1. **Cache storage**
   - SQLite database in `~/.complexionist/cache.db`
   - Or JSON files in `~/.complexionist/cache/`

2. **Cache operations**
   - Store with TTL
   - Lookup before API call
   - Invalidate on `--no-cache`
   - Clear with `complexionist cache --clear`

3. **Cache targets**
   | Data | TTL |
   |------|-----|
   | TMDB movie details | 7 days |
   | TMDB collections | 7 days |
   | TVDB episodes | 24 hours |

**Deliverable:** Faster subsequent runs.

---

## Phase 8: GUI (v2.0 - Future)

**Goal:** Desktop or web-based interface.

### Options to evaluate:

1. **PyQt / PySide6**
   - Native desktop app
   - Cross-platform
   - Steeper learning curve

2. **Textual**
   - Terminal UI (TUI)
   - Very Pythonic
   - Runs in terminal, but rich interface

3. **Web-based (FastAPI + React/Vue)**
   - Modern, familiar
   - Requires more infrastructure
   - Could run locally

4. **Electron + Python backend**
   - Desktop app with web tech
   - Larger footprint

**Decision deferred** until CLI is stable.

---

## Development Milestones

| Milestone | Phases | Description |
|-----------|--------|-------------|
| M1 | 0-1 | Project setup + Plex connection |
| M2 | 2-3 | Movie collection gaps working |
| M3 | 4-5 | TV episode gaps working |
| M4 | 6 | CLI polish, v1.0 release |
| M5 | 7 | Caching, v1.1 release |
| M6 | 8 | GUI, v2.0 release |

---

## Testing Strategy

### Unit Tests
- Mock Plex, TMDB, TVDB responses
- Test gap detection logic
- Test multi-episode parsing
- Test filtering (future, specials)

### Integration Tests
- Test against real APIs with test data
- Require API keys (skip in CI without secrets)

### Manual Testing
- Test with real Plex server
- Verify output matches expected gaps

---

## Risk Mitigation

| Risk | Mitigation |
|------|------------|
| TMDB rate limits | Caching, backoff, batch requests |
| TVDB rate limits | Caching, backoff |
| Movies without TMDB ID | Skip gracefully, warn in verbose |
| Shows without TVDB GUID | Skip gracefully, warn in verbose |
| Plex API changes | Pin plexapi version, test regularly |
| TMDB/TVDB API changes | Monitor changelogs, version endpoints |
