# Reference Implementation Analysis

Analysis of existing tools that solve similar problems to ComPlexionist.

---

## 1. Gaps (Movie Collection Gaps)

**Repository:** https://github.com/adamus1red/gaps
**Language:** Java (Spring Boot backend), JavaScript (jQuery/Bootstrap frontend)
**Status:** No longer actively maintained

### How It Works

1. **Plex Connection:** Token-based auth via `X-Plex-Token`, configured with server IP/port
2. **TMDB Integration:** Requires user's TMDB API key to query collection data
3. **Workflow:**
   - Scans Plex movie library
   - For each movie, queries TMDB for collection membership
   - Identifies other movies in the same collection
   - Reports movies not in user's Plex library
4. **Output:** Web UI with paginated results, RSS feed support

### Key Data Structures

**BasicMovie** (movie in Plex):
- `name`, `year`, `overview`, `language`
- `tmdbId`, `imdbId`, `ratingKey`
- `collectionId`, `collectionTitle`
- `posterUrl`, `backdropUrl`
- `genres` (list)
- `moviesInCollection` (list)

**MovieFromCollection** (movie from TMDB collection):
- `title`, `tmdbId`, `year`
- `owned` (boolean - whether user has it)

### Key Observations

- Uses TMDB collection IDs to get complete collection membership
- Parses Plex XML responses (not JSON)
- Matches movies by TMDB ID for ownership detection
- Handles movies without collection membership gracefully

---

## 2. WebTools-NG (General Purpose)

**Repository:** https://github.com/WebTools-NG/WebTools-NG
**Language:** JavaScript (Vue.js + Electron)
**Status:** Active

### Relevance to ComPlexionist

WebTools-NG is primarily an **export/reporting tool**, not a missing content detector. It:
- Exports Plex library metadata to Excel/CSV
- Manages server settings
- Does NOT have missing episode detection

**Verdict:** Limited usefulness for our specific features. The Plex connection patterns may be useful reference.

### Plex Connection Pattern

```javascript
header['X-Plex-Token'] = payload.Token;
// Used for all API calls
```

---

## 3. PlexMissingEpisodes (TV Episode Gaps)

**Repository:** https://github.com/MysticRyuujin/PlexMissingEpisodes
**Language:** PowerShell
**Status:** Active

### How It Works

1. **Plex Authentication:**
   - Token-based: Direct `$PlexToken` parameter
   - Credential-based: Username/password → `https://plex.tv/users/sign_in.json` → token
   - Headers: `X-Plex-Client-Identifier`, `X-Plex-Product`, `X-Plex-Version`, `X-Plex-Token`

2. **TVDB Integration:**
   - Base URL: `https://api4.thetvdb.com/v4/`
   - Auth: `POST /login` with apikey → Bearer token
   - Episodes: `GET /series/{id}/episodes/default?page={n}` (paginated)

3. **Comparison Algorithm:**
   ```
   For each show in Plex:
     Get TVDB GUID from Plex metadata
     Fetch all episodes from TVDB for that series
     Filter out:
       - Unaired episodes
       - Season 0 (specials) unless flag set
       - Episodes aired < 24 hours ago
     For each TVDB episode:
       Check if season exists in Plex
       Search for episode by number OR by name
       If not found → mark as missing
   ```

4. **Multi-Episode File Handling:**
   - Parses filenames for ranges like `S02E01-02` or `S02E01-E02`
   - `Get-EpisodeNumbers` function extracts individual episode numbers
   - Prevents false positives for combined episode files

### Key Data Structures

**$PlexShows** (hashtable):
```
{
  "tvdb://12345": {
    "title": "Show Name",
    "year": 2020,
    "ratingKeys": [...],
    "seasons": {
      1: [{ episodeNum: "Episode Title" }, ...],
      2: [...],
    }
  }
}
```

**$Missing** (hashtable):
```
{
  "tvdb://12345": [
    { airedSeason: 2, airedEpisodeNumber: 5, episodeName: "Episode Title" },
    ...
  ]
}
```

### Output Formats

**Simple:** `Show Name (Year) - SXXEXX - Title`

**Standard:** Grouped by show, then season, with counts and smart truncation for large gaps.

### Key Observations

- Uses TVDB GUID stored in Plex metadata to link shows
- Handles pagination for TVDB episode lists
- Smart filtering (no specials, no future episodes)
- Filename parsing for multi-episode detection is crucial
- Can exclude specific shows via filter list

---

## Recommendations for ComPlexionist

### Authentication
- Support both token-based and username/password auth for Plex
- Store tokens securely (not in code)
- TMDB and TVDB both require API keys (free tier available)

### Movie Collections Feature
Based on Gaps approach:
1. Fetch all movies from Plex library
2. For each movie, get TMDB ID from Plex metadata
3. Query TMDB for movie details including `belongs_to_collection`
4. If in collection, fetch full collection from TMDB
5. Compare collection movies against Plex library (by TMDB ID)
6. Report missing movies

### TV Episodes Feature
Based on PlexMissingEpisodes approach:
1. Fetch all TV shows from Plex library
2. For each show, get TVDB GUID from Plex metadata
3. Query TVDB for all episodes in series
4. Filter out specials (optional), unaired, very recent
5. Compare against Plex episodes (by season/episode number AND name)
6. Handle multi-episode files via filename parsing
7. Report missing episodes

### Data Sources Priority
- **Movies:** TMDB (has collection data)
- **TV Shows:** TVDB (more comprehensive episode data) or TMDB (alternative)

### Tech Stack Considerations
- **Python** recommended: `python-plexapi` library is mature and well-documented
- Avoid Java complexity (Gaps is over-engineered for our needs)
- PowerShell approach works but limits cross-platform
- Consider CLI + optional web UI

---

## API Endpoints Summary

### Plex Media Server
```
GET /library/sections                     # List libraries
GET /library/sections/{id}/all            # All items in library
GET /library/metadata/{id}                # Item details
GET /library/metadata/{id}/children       # Seasons (for shows)
GET /library/metadata/{id}/allLeaves      # All episodes (for shows)
```

### TMDB
```
GET /movie/{id}                           # Movie details (includes collection info)
GET /collection/{id}                      # Full collection with all movies
GET /search/collection?query={name}       # Search collections by name
```

**Important TMDB Data Notes:**
- TMDB returns `release_date` as an ISO date string (e.g., "1999-10-15"), NOT a `year` field
- Must parse `release_date` to extract year: `date.fromisoformat(release_date).year`
- `release_date` can be `null` or empty string for unreleased/unknown movies
- `belongs_to_collection` is `null` if movie is not part of a collection
- Collection parts may include unreleased movies (check `release_date` before today)

### TVDB v4
```
POST /login                               # Auth with API key
GET /series/{id}/episodes/default         # All episodes (paginated)
GET /search?query={name}&type=series      # Search shows
```

---

## Implementation Learnings (v1.1)

Lessons learned from building and releasing ComPlexionist v1.1.

### PyInstaller Bundling

When bundling Python apps with PyInstaller:
- `__file__` points to a temp extraction directory, not a valid filesystem path
- Avoid using `Path(__file__).parent` as `cwd` for subprocess calls
- Git operations fail inside bundled executables (no `.git` directory)
- Version numbers must be baked in at build time or use fallback values

### Pydantic Models

When using Pydantic for API response models:
- Use `@property` decorators for computed fields (like `year` from `release_date`)
- Ensure all model classes that access the same data have consistent properties
- `TMDBMovie` and `TMDBMovieDetails` should have identical property interfaces

### GitHub Actions

- `GITHUB_TOKEN` needs explicit `permissions: contents: write` to create releases
- Use `fetch-depth: 0` in checkout for commit count versioning
- Test executables in CI before creating releases (`--version`, `--help`)
- `softprops/action-gh-release@v2` with `body_path` for custom release notes

### Versioning

Commit-count based versioning (`1.1.{commit_count}`) works well:
- No manual version bumping needed for patches
- Consistent between source and built executables
- Falls back gracefully when git unavailable

### User Experience

From first-run feedback:
- Users have multiple libraries (Kids Movies, Movies) - need library selection
- `.env` files feel too technical - prefer `.cfg` format
- Progress indicators that replace lines hide completed work
- CSV output should be automatic, not manual
