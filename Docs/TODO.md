# ComPlexionist - Development TODO

## Current Focus: Phase 8 - GUI (v2.0)

Next up: Evaluate GUI options and design UI/UX

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

---

## Upcoming Phases

### Phase 7.6: UX Improvements (v1.2)
Based on initial release feedback:

**Library Selection**
- [ ] Add `--library` flag to specify which library to scan
- [ ] Support multiple libraries (e.g., "Movies" and "Kids Movies")
- [ ] List available libraries when not specified

**Output Improvements**
- [ ] Default to writing CSV alongside terminal output
- [ ] CSV auto-saved to working directory (e.g., `movies_gaps_2026-01-25.csv`)
- [ ] Add `--no-csv` flag to disable automatic CSV

**Configuration**
- [ ] Switch from `.env` to `complexionist.cfg` (more user-friendly)
- [ ] Support both formats during transition
- [ ] Auto-migrate `.env` to `.cfg` on first run

**Cache Redesign**
- [ ] Cache always enabled (remove `--no-cache` concept)
- [ ] Single cache file per library name (not per API call)
- [ ] Cache invalidation based on Plex library update timestamp
- [ ] `cache refresh` command to force re-fetch

**Progress Display**
- [ ] Use line breaks instead of line replacement for progress phases
- [ ] User can see completed phases while current phase runs
- [ ] Summary at end shows all phases with timing

### Phase 8: GUI (v2.0)
- [ ] Evaluate GUI options (PyQt, Textual, Web)
- [ ] Design UI/UX
- [ ] Implement GUI

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
