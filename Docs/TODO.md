# ComPlexionist - Development TODO

## Current Focus: Phase 6 - CLI Polish (v1.0)

- [ ] Configuration file support (YAML)
- [ ] Show exclusion list for TV episodes
- [ ] Recent episode threshold (24h) filtering
- [ ] `--quiet` flag for minimal output
- [ ] `--min-collection-size` for filtering small collections
- [ ] Comprehensive error handling review

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

---

## Upcoming Phases

### Phase 6: CLI Polish (v1.0)
- [x] Wire movie gap detection into CLI `movies` command
- [x] JSON output format (movies)
- [x] CSV output format (movies)
- [x] Progress indicators with Rich
- [x] Wire episode gap detection into CLI `episodes` command
- [x] JSON output format (episodes)
- [x] CSV output format (episodes)
- [ ] Configuration file support (YAML)
- [ ] Show exclusion list
- [ ] Recent episode threshold (24h)
- [ ] Comprehensive error handling

### Phase 7: Caching (v1.1)
- [ ] Design cache storage (SQLite or JSON)
- [ ] Implement TTL-based caching
- [ ] `--no-cache` flag
- [ ] `cache --clear` command

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
