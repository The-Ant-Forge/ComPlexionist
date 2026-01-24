# ComPlexionist - Development TODO

## Current Focus: Phase 0 - Project Setup

- [ ] Initialize Python project with `pyproject.toml`
- [ ] Set up virtual environment
- [ ] Install core dependencies (plexapi, httpx, click/typer, etc.)
- [ ] Create package structure (`src/complexionist/`)
- [ ] Create `.env.example` with required credentials
- [ ] Set up Ruff for linting/formatting
- [ ] Create basic CLI entry point (`complexionist --help`)

---

## Phase 1: Plex Integration

- [ ] Implement Plex authentication (token-based)
- [ ] List available libraries
- [ ] Extract movies with TMDB IDs
- [ ] Extract TV shows with TVDB GUIDs
- [ ] Extract episodes with season/episode numbers
- [ ] Handle missing external IDs gracefully

## Phase 2: TMDB Integration

- [ ] Create TMDB API client
- [ ] Implement movie details endpoint (get collection info)
- [ ] Implement collection endpoint (get all movies)
- [ ] Handle rate limiting with backoff

## Phase 3: Movie Gap Detection

- [ ] Build owned movie set from Plex
- [ ] Query TMDB for collection membership
- [ ] Fetch full collections
- [ ] Filter future releases
- [ ] Compare and generate missing movies report

## Phase 4: TVDB Integration

- [ ] Create TVDB v4 API client
- [ ] Implement login/token flow
- [ ] Implement series episodes endpoint (paginated)
- [ ] Handle rate limiting

## Phase 5: Episode Gap Detection

- [ ] Build owned episode map from Plex
- [ ] Parse multi-episode filenames (S02E01-02)
- [ ] Query TVDB for complete episode lists
- [ ] Filter: future, specials, very recent
- [ ] Compare and generate missing episodes report

## Phase 6: CLI Polish

- [ ] Unified `scan` command
- [ ] JSON output format
- [ ] CSV output format
- [ ] Progress indicators with Rich
- [ ] Configuration file support
- [ ] Comprehensive error handling

## Phase 7: Caching (v1.1)

- [ ] Design cache storage (SQLite or JSON)
- [ ] Implement TTL-based caching
- [ ] `--no-cache` flag
- [ ] `cache --clear` command

## Phase 8: GUI (v2.0)

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
- [ ] User guide
- [ ] API key setup instructions
