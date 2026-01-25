# ComPlexionist v1.2 - UX Improvements

**Release Date:** January 2026
**Version:** 1.2.26

---

## Overview

This major release delivers a complete overhaul of the user experience based on initial release feedback. ComPlexionist is now much easier to set up and use, with an interactive setup wizard, improved configuration, smarter caching, and detailed summary reports.

---

## What's New in v1.2

### First-Run Setup Wizard
- Automatic detection of missing configuration
- Interactive prompts for Plex URL/token, TMDB key, TVDB key
- **Live validation** - credentials are tested as you enter them
- Creates `complexionist.ini` automatically
- Offers dry-run validation after setup

### New Configuration System
- **INI format** (`complexionist.ini`) - more readable than `.env` files
- **Portable config search order:** exe directory → current directory → home directory
- Backwards compatible - existing `.env` files still work
- New commands: `config setup`, `config show`, `config path`

### Library Selection
- New `--library` / `-l` flag for both `movies` and `tv` commands
- Support multiple libraries: `--library "Movies" --library "Kids Movies"`
- Lists available libraries when not specified

### Collection Filtering
- New `--min-owned` flag (default: 2)
- Only report gaps for collections where you own N+ movies
- Reduces noise from single-movie collections

### Automatic CSV Output
- CSV files auto-saved alongside terminal output
- Format: `{Library}_movies_gaps_{date}.csv` or `{Library}_tv_gaps_{date}.csv`
- New `--no-csv` flag to disable automatic CSV

### Cache Redesign
- **Single portable JSON file:** `complexionist.cache.json` (next to config)
- **Fingerprint-based invalidation** - detects when library content changes
- Batched saves for Windows compatibility
- Removed `--no-cache` (cache always enabled for performance)
- New `cache refresh` command to force re-fetch

### Dry-Run Mode
- New `--dry-run` flag validates config without running full scan
- Shows: Plex connection status, available libraries, API key validity
- Useful for testing setup before long-running scans

### Summary Reports
- ComPlexionist banner on startup
- **Completion score** - percentage of collection/episodes owned
- Stats: items analyzed, gaps found, scan duration
- Performance: API calls made, cache hits/misses
- Top 3 TV shows with most missing episodes

### Command Rename
- `episodes` command renamed to `tv` (more intuitive)
- Usage: `complexionist tv` instead of `complexionist episodes`

---

## Bug Fixes

- Fixed missing year property on TMDBMovieDetails
- Fixed trailing whitespace in ASCII banner
- Fixed unused variable warnings
- Fixed cache file structure tests for batched saves

---

## Breaking Changes

**None** - `.env` files still work as fallback, and all existing CLI options remain supported.

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

## Quick Start

### Option 1: Setup Wizard (Recommended)
```bash
complexionist config setup
```
The wizard will guide you through entering all credentials with live validation.

### Option 2: Manual Configuration
Create `complexionist.ini` next to the executable:
```ini
[plex]
url = http://your-plex-server:32400
token = your-plex-token

[tmdb]
api_key = your-tmdb-api-key

[tvdb]
api_key = your-tvdb-api-key
```

### Run a Scan
```bash
# Find missing movies
complexionist movies

# Find missing TV episodes
complexionist tv

# Validate config first
complexionist movies --dry-run
```

---

## Command Reference

### Main Commands
| Command | Description |
|---------|-------------|
| `movies` | Find missing movies from collections |
| `tv` | Find missing TV episodes (renamed from `episodes`) |
| `scan` | Run both movies and TV scans |
| `config setup` | Run interactive setup wizard |
| `config show` | Display current configuration |
| `config path` | Show configuration file paths |
| `cache stats` | Display cache statistics |
| `cache clear` | Clear all cached data |
| `cache refresh` | Invalidate fingerprints for re-fetch |

### New Options in v1.2
| Option | Description |
|--------|-------------|
| `--library`, `-l` | Select specific library to scan |
| `--min-owned N` | Minimum owned movies to report collection |
| `--dry-run` | Validate config without scanning |
| `--no-csv` | Disable automatic CSV output |

### Existing Options
| Option | Description |
|--------|-------------|
| `-v, --verbose` | Show detailed progress |
| `-q, --quiet` | Minimal output |
| `-f, --format` | Output format: `text`, `json`, or `csv` |
| `--include-future` | Include unreleased content |
| `--include-specials` | Include Season 0 |
| `--recent-threshold N` | Skip recently aired episodes |
| `--exclude-show "Name"` | Exclude a specific show |

---

## What's Next

### Planned for v2.0
- **GUI Application:** Desktop interface for easier use
- Potential TUI (Terminal UI) with Textual
- Or native GUI with PyQt/PySide

---

## Support & Contributing

- **Issues:** [GitHub Issues](https://github.com/StephKoenig/ComPlexionist/issues)
- **Repository:** [GitHub](https://github.com/StephKoenig/ComPlexionist)

---

## License

MIT License - See [LICENSE](LICENSE) for details.
