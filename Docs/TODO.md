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

## Upcoming Phases

### Phase 9: GUI (v2.0)
- [ ] Evaluate GUI options (PyQt, Textual, Web)
- [ ] Design UI/UX
- [ ] Implement GUI

---

## Future Optimizations

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
