# ComPlexionist

[![Python](https://github.com/StephKoenig/ComPlexionist/actions/workflows/ci.yml/badge.svg)](https://github.com/StephKoenig/ComPlexionist/actions/workflows/ci.yml)
[![Windows](https://github.com/StephKoenig/ComPlexionist/actions/workflows/build.yml/badge.svg)](https://github.com/StephKoenig/ComPlexionist/actions/workflows/build.yml)

Completing your Plex Media Server libraries.

## Features

### Movie Collection Gaps
Plex automatically creates Collections when you own movies that belong to a franchise (e.g., "Alien Collection", "Star Wars Collection"). However, Plex doesn't tell you which movies from those collections you're missing.

ComPlexionist solves this by:
- Scanning your Plex movie library collections
- Cross-referencing with TMDB (The Movie Database) to get the complete collection
- Listing all missing movies from each collection

### TV Episode Gaps
For TV show libraries, ComPlexionist identifies missing episodes:
- Scans your Plex TV library for series
- Cross-references with TVDB for complete episode listings
- Reports missing episodes by season
- Handles multi-episode files (S02E01-02, S02E01-E02, etc.)

### Caching
API responses are cached to reduce redundant calls and speed up subsequent scans:
- TMDB movie/collection data: 7 days
- TVDB episode data: 24 hours
- Cache stored next to config file (or exe) as human-readable JSON
- Automatic invalidation when library content changes

## Prerequisites

- Python 3.11+
- Plex Media Server with configured libraries
- Plex authentication token ([how to find](https://support.plex.tv/articles/204059436-finding-an-authentication-token-x-plex-token/))
- TMDB API key ([register free](https://www.themoviedb.org/settings/api))
- TVDB API key ([register](https://thetvdb.com/api-information))

## Installation

```bash
# Clone the repository
git clone https://github.com/StephKoenig/ComPlexionist.git
cd ComPlexionist

# Create virtual environment and install
python -m venv .venv
.venv/Scripts/activate  # Windows
# source .venv/bin/activate  # Linux/Mac

pip install -e ".[dev]"
```

## Configuration

### First-Run Setup
On first run, ComPlexionist will detect missing configuration and offer to run the setup wizard:

```bash
complexionist config setup
```

This interactively creates a `complexionist.ini` file with your credentials.

### Configuration File
Create a `complexionist.ini` file (next to the exe, in current directory, or in `~/.complexionist/`):

```ini
[plex]
url = http://your-plex-server:32400
token = your-plex-token

[tmdb]
api_key = your-tmdb-api-key

[tvdb]
api_key = your-tvdb-api-key

[options]
exclude_future = true
exclude_specials = true
recent_threshold_hours = 24
min_collection_size = 2
min_owned = 2

[exclusions]
# shows = Daily Talk Show, Another Show
# collections = Anthology Collection
```

See `complexionist.ini.example` for a full template with comments.

## Usage

### Find Missing Movies

```bash
# Scan movie library for collection gaps
complexionist movies

# Scan specific library (by name)
complexionist movies --library "Movies 4K"

# Include unreleased movies
complexionist movies --include-future

# Output as JSON
complexionist movies --format json

# Skip small collections (less than 3 movies)
complexionist movies --min-collection-size 3

# Only show collections where you own at least 3 movies
complexionist movies --min-owned 3

# Suppress automatic CSV output
complexionist movies --no-csv
```

### Find Missing TV Episodes

```bash
# Scan TV library for episode gaps
complexionist tv

# Scan specific library (by name)
complexionist tv --library "TV Shows 4K"

# Include specials (Season 0)
complexionist tv --include-specials

# Include unaired episodes
complexionist tv --include-future

# Exclude specific shows
complexionist tv --exclude-show "Daily Talk Show"

# Skip recently aired (within 48 hours)
complexionist tv --recent-threshold 48

# Suppress automatic CSV output
complexionist tv --no-csv
```

### Scan Both Libraries

```bash
complexionist scan
```

### Cache Management

```bash
# View cache statistics
complexionist cache stats

# Clear all cached data
complexionist cache clear

# Force refresh (invalidate fingerprints)
complexionist cache refresh
```

### Configuration Commands

```bash
# Show current configuration
complexionist config show

# Show config file paths
complexionist config path

# Run interactive setup wizard
complexionist config setup

# Validate configuration (dry-run)
complexionist config validate
```

### Common Options

```bash
# Quiet mode (no progress indicators)
complexionist -q movies

# Verbose mode
complexionist -v movies

# Dry-run mode (validate config without scanning)
complexionist movies --dry-run

# Output formats: text (default), json, csv
complexionist movies --format json
complexionist tv --format csv
```

## Example Output

```
Movie Collection Gaps - Movies

Summary:
  Movies scanned: 1,234
  In collections: 89
  Collections with gaps: 12

Alien Collection (missing 2 of 6):
  - Alien³ (1992)
  - Alien Resurrection (1997)

Terminator Collection (missing 1 of 6):
  - Terminator: Dark Fate (2019)
```

## Documentation

- [Plex Background Research](Docs/Plex-Background.md) - Technical details about Plex API
- [Specification](Docs/Specification.md) - Feature specs and architecture
- [Completed Work](Docs/Completed.md) - Development history

## License

MIT

## Acknowledgments

- [Plex](https://www.plex.tv/) - Media server platform
- [TMDB](https://www.themoviedb.org/) - Movie metadata
- [TVDB](https://thetvdb.com/) - TV show metadata
- [python-plexapi](https://github.com/pkkid/python-plexapi) - Python bindings for Plex API
