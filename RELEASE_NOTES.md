# ComPlexionist v1.1.14 - Initial Release

**Release Date:** January 2026
**Version:** 1.1.14

---

## Overview

ComPlexionist is a command-line tool that identifies missing content in your Plex Media Server libraries. It helps you discover gaps in your movie collections and TV series by cross-referencing your Plex library against TMDB and TVDB databases.

---

## Key Features

### Movie Collection Gap Detection
- Automatically detects incomplete movie collections in your Plex library
- Cross-references with TMDB (The Movie Database) for accurate collection data
- Identifies which movies you're missing from franchises like "Alien Collection", "Star Wars Collection", etc.
- Filters out unreleased movies by default
- Configurable minimum collection size threshold

### TV Episode Gap Detection
- Scans TV libraries for missing episodes
- Cross-references with TVDB for complete episode listings
- Handles multi-episode files (S02E01-02, S02E01-E02, S02E01E02)
- Filters out future episodes and specials (Season 0) by default
- Configurable recent episode threshold to avoid false positives for just-aired content
- Show exclusion list for skipping daily shows, talk shows, etc.

### Smart Caching
- API responses cached to reduce redundant calls and speed up subsequent scans
- TMDB movie/collection data: 7-day cache
- TVDB episode data: 24-hour cache
- Human-readable JSON cache files in `~/.complexionist/cache/`
- `--no-cache` flag to bypass cache when needed
- Cache management commands (`cache clear`, `cache stats`)

### Multiple Output Formats
- **Text** (default): Human-readable formatted output
- **JSON**: Machine-readable for automation and scripting
- **CSV**: Spreadsheet-friendly for further analysis

### Configuration
- YAML configuration file support (`~/.complexionist/config.yaml`)
- Environment variable support via `.env` file
- Persistent exclusion lists for shows and collections
- Configurable defaults for all filtering options

---

## Requirements

### System Requirements
- **Python:** 3.11 or higher (for source installation)
- **Windows:** Windows 10/11 (for standalone executable)
- **Network:** Access to your Plex server and internet for API calls

### API Keys Required
| Service | Purpose | How to Get |
|---------|---------|------------|
| **Plex Token** | Access your Plex server | [Finding your Plex token](https://support.plex.tv/articles/204059436-finding-an-authentication-token-x-plex-token/) |
| **TMDB API Key** | Movie collection data | [Register free at TMDB](https://www.themoviedb.org/settings/api) |
| **TVDB API Key** | TV episode data | [Register at TVDB](https://thetvdb.com/api-information) |

---

## Available Builds

### Windows Executable
**File:** `complexionist.exe`
**Platform:** Windows 10/11 (64-bit)
**Size:** ~15-20 MB (standalone, no Python required)

The Windows executable is a self-contained binary that includes all dependencies. Simply download and run from any directory.

```cmd
# Check version
complexionist.exe --version

# Find missing movies
complexionist.exe movies

# Find missing episodes
complexionist.exe episodes
```

### Python Package (Source)
**Platforms:** Windows, macOS, Linux
**Requires:** Python 3.11+

Install from source for any platform:

```bash
git clone https://github.com/StephKoenig/ComPlexionist.git
cd ComPlexionist
python -m venv .venv
.venv/Scripts/activate  # Windows
# source .venv/bin/activate  # Linux/Mac
pip install -e .
```

---

## Quick Start

### 1. Configure Credentials
Create a `.env` file in your working directory:

```bash
PLEX_URL=http://your-plex-server:32400
PLEX_TOKEN=your-plex-token
TMDB_API_KEY=your-tmdb-api-key
TVDB_API_KEY=your-tvdb-api-key
```

### 2. Initialize Configuration (Optional)
```bash
complexionist config init
```

### 3. Find Missing Content
```bash
# Scan movie collections
complexionist movies

# Scan TV episodes
complexionist episodes

# Scan both
complexionist scan
```

---

## Command Reference

### Main Commands
| Command | Description |
|---------|-------------|
| `movies` | Find missing movies from collections |
| `episodes` | Find missing TV episodes |
| `scan` | Run both movies and episodes scans |
| `config show` | Display current configuration |
| `config path` | Show configuration file paths |
| `config init` | Create default config file |
| `cache stats` | Display cache statistics |
| `cache clear` | Clear all cached data |

### Common Options
| Option | Description |
|--------|-------------|
| `-v, --verbose` | Show detailed progress and information |
| `-q, --quiet` | Minimal output (no progress indicators) |
| `--no-cache` | Bypass cache, fetch fresh data |
| `-f, --format` | Output format: `text`, `json`, or `csv` |

### Movie-Specific Options
| Option | Description |
|--------|-------------|
| `--include-future` | Include unreleased movies |
| `--min-collection-size N` | Only show collections with N+ movies |

### Episode-Specific Options
| Option | Description |
|--------|-------------|
| `--include-future` | Include unaired episodes |
| `--include-specials` | Include Season 0 (specials) |
| `--recent-threshold N` | Skip episodes aired within N hours |
| `--exclude-show "Name"` | Exclude a specific show |

---

## Example Output

### Movie Collections
```
Movie Collection Gaps

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

### TV Episodes
```
TV Episode Gaps

Summary:
  Shows scanned: 156
  Shows with gaps: 23

Breaking Bad (missing 3 episodes):
  Season 2:
    - S02E05 - Breakage
    - S02E06 - Peekaboo
  Season 4:
    - S04E11 - Crawl Space
```

---

## Known Limitations

- **Plex Match Required:** Only works with content that Plex has matched to TMDB/TVDB
- **External IDs Required:** Movies need TMDB IDs, TV shows need TVDB GUIDs
- **Rate Limits:** First scan may be slow due to API rate limiting (cached subsequent runs are fast)
- **Windows Only:** Standalone executable is Windows-only (use Python package for other platforms)

---

## What's Next

### Planned for v2.0
- **GUI Application:** Desktop interface for easier use
- Potential TUI (Terminal UI) with Textual
- Or native GUI with PyQt/PySide

### Future Considerations
- macOS and Linux standalone executables
- Radarr/Sonarr integration
- Notification system for new gaps
- Multiple Plex server support

---

## Support & Contributing

- **Issues:** [GitHub Issues](https://github.com/StephKoenig/ComPlexionist/issues)
- **Repository:** [GitHub](https://github.com/StephKoenig/ComPlexionist)

---

## License

MIT License - See [LICENSE](LICENSE) for details.

---

## Acknowledgments

- [Plex](https://www.plex.tv/) - Media server platform
- [TMDB](https://www.themoviedb.org/) - Movie metadata
- [TVDB](https://thetvdb.com/) - TV show metadata
- [python-plexapi](https://github.com/pkkid/python-plexapi) - Python bindings for Plex API
