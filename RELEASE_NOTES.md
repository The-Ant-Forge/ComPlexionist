# ComPlexionist v2.0 - Desktop GUI

**Release Date:** January 2026
**Version:** 2.0.62

---

## Overview

ComPlexionist v2.0 is a major release introducing a full **desktop graphical user interface** built with the Flet framework. The GUI is now the default mode when running the application, making it easier than ever to find missing movies and TV episodes in your Plex library.

---

## Major New Features

### Desktop GUI Application
A complete graphical interface with professional-quality user experience:

**Dashboard**
- Connection status indicators for Plex, TMDB, and TVDB
- Quick scan buttons for Movies, TV Shows, or Full Scan
- Direct access to Settings

**Scanning Screen**
- Real-time progress bar with phase indicators
- Live statistics display: Duration, API calls (Plex/TMDB/TVDB), Cache hit rate
- Cancel button to abort long-running scans
- Granular progress during initialization phases

**Results Screen**
- Grouped display by collection (movies) or show (TV)
- Expandable tiles showing owned items (green checkmarks) and missing items
- Search filter for collection names, movie titles, and show names
- Poster images with clickable links to TMDB/TVDB
- Completion score with color-coded rating (green/orange/red)
- Export functionality: CSV, JSON, or clipboard copy

**Ignore Functionality**
- Click to ignore collections or shows directly from results
- Ignored items are saved to your INI config file
- Ignored items are automatically skipped in future scans
- Manage ignore lists from the Settings screen

**Settings Screen**
- View and edit configuration
- Re-run setup wizard
- Manage ignore lists
- View config file path

**Window State Persistence**
- Window size and position saved automatically
- Restored on next launch

### Default GUI Mode
- Running `complexionist` without arguments now launches the GUI
- Use `--cli` flag for command-line mode: `complexionist --cli`
- Subcommands (movies, tv, scan) still work directly

### CLI Integration with GUI
- New `--use-ignore-list` flag for movies, tv, and scan commands
- Respects ignore lists managed via GUI
- Example: `complexionist movies --use-ignore-list`

---

## Code Quality Improvements

### Shared Modules (v1.3 Consolidation)
Code consolidation reducing duplication between CLI and GUI:

- **`constants.py`** - Centralized color constants (PLEX_GOLD), score thresholds
- **`errors.py`** - Shared error message handling for both CLI and GUI
- **`validation.py`** - Connection testing with `test_connections()` function
- **`statistics.py`** - Unified scan statistics tracking with duration formatting

### API Client Improvements
- Unified exception hierarchy (`APIError`, `APIAuthError`, `APINotFoundError`, `APIRateLimitError`)
- TMDB/TVDB clients share common error handling patterns
- `parse_date()` helper for consistent date parsing

### Model Mixins
- `EpisodeCodeMixin` - Provides `episode_code` property (S01E05 format)
- `DateAwareMixin` - Date comparison helpers

### Conditional Cache TTL
- Movies WITH collection membership: 30 days
- Movies WITHOUT collection: 7 days
- Collections: 30 days
- Reduces API calls for stable data

### Clean Type Checking
- All MyPy errors resolved
- Clean type checking in CI (no longer informational-only)
- Fixed field alias mismatch bugs discovered via type checking

---

## Bug Fixes

### GUI Stability
- Fixed `ConnectionResetError` spam on Windows when closing GUI
- Clean window close handling with proper asyncio shutdown
- Fixed FilePicker dialog compatibility with Flet desktop

### Data Display
- Fixed alignment issues in results display
- Fixed season rollup optimization for TV episodes
- Episode titles now shown in TV results
- Proper grouping of episodes by season

### API Fixes
- Fixed `first_aired` -> `firstAired` field name in TVDB client
- Fixed cache structure for TVDB episodes (wrapped in proper dict)
- Fixed `belongs_to_collection` passing raw dict instead of model

### Performance
- Lazy module imports for faster startup
- Banner displays immediately while heavy modules load
- Optimized ignore button UI updates

---

## Breaking Changes

**None** - All existing CLI options and `.env`/INI configuration files continue to work.

### Behavior Change
- Default mode is now GUI instead of CLI
- To use CLI, either:
  - Add `--cli` flag: `complexionist --cli`
  - Use a subcommand directly: `complexionist movies`

---

## Distribution

### Single-File Executable
- Windows executable bundled with Flet desktop client (~57 MB)
- No Python installation required
- Both GUI and CLI modes from same executable
- Application icon embedded

### Build Configuration
- PyInstaller spec file for reproducible builds
- Hidden imports configured for all dependencies
- Flet desktop data files bundled

---

## Requirements

### System Requirements
- **Windows:** Windows 10/11 (for standalone executable)
- **Python:** 3.11+ (for source installation)
- **Network:** Access to your Plex server and internet for API calls

### API Keys Required
| Service | Purpose | How to Get |
|---------|---------|------------|
| **Plex Token** | Access your Plex server | [Finding your Plex token](https://support.plex.tv/articles/204059436-finding-an-authentication-token-x-plex-token/) |
| **TMDB API Key** | Movie collection data | [Register free at TMDB](https://www.themoviedb.org/settings/api) |
| **TVDB API Key** | TV episode data | [Register at TVDB](https://thetvdb.com/api-information) |

---

## Quick Start

### GUI Mode (Recommended)
1. Download `complexionist.exe` from this release
2. Run the executable - GUI launches automatically
3. If no configuration exists, the setup wizard guides you through setup
4. Click "Movies", "TV Shows", or "Full Scan" to find gaps

### CLI Mode
```bash
# Interactive CLI mode
complexionist --cli

# Direct commands
complexionist movies
complexionist tv
complexionist scan

# With ignore list
complexionist movies --use-ignore-list
```

---

## New CLI Options

| Option | Command | Description |
|--------|---------|-------------|
| `--cli` | main | Force CLI mode instead of GUI |
| `--gui` | main | Explicitly launch GUI (default) |
| `--use-ignore-list` | movies, tv, scan | Use GUI-managed ignore lists |

---

## Technical Details

### GUI Framework
- Built with [Flet](https://flet.dev/) (Python framework based on Flutter)
- Dark mode theme with Plex gold accent color (#E5A00D)
- Thread-safe UI updates via pubsub mechanism
- Async window close handling for Windows compatibility

### GUI Package Structure
```
src/complexionist/gui/
  __init__.py        # Package exports (run_app)
  app.py             # Main app, navigation, scan execution
  state.py           # AppState dataclass (all UI state)
  theme.py           # Plex gold theme configuration
  strings.py         # UI strings (i18n ready)
  errors.py          # GUI error display helpers
  window_state.py    # Window size/position persistence
  screens/
    base.py          # BaseScreen abstract class
    dashboard.py     # Home screen with scan buttons
    onboarding.py    # First-run setup wizard
    results.py       # Results with search/export/ignore
    scanning.py      # Progress display with live stats
    settings.py      # Settings panel
```

---

## Upgrade Notes

### From v1.2
- Your existing `complexionist.ini` works without changes
- Cache files are compatible
- First launch will now show GUI instead of CLI
- Add `--cli` if you prefer command-line mode

### From v1.1 or earlier
- Run `complexionist config setup` to create INI config
- Or continue using `.env` file (still supported)

---

## What's Next

### Planned for v2.1
- Browser extension for Chrome/Firefox
- Same core functionality without installation
- Config stored in browser sync storage

---

## Commits Since Last Release

This release includes 32 commits with:
- Full GUI implementation (Phases 9a.1-9a.6)
- Code consolidation and shared modules
- MyPy cleanup for clean type checking
- Multiple bug fixes and performance improvements

---

## Support & Contributing

- **Issues:** [GitHub Issues](https://github.com/StephKoenig/ComPlexionist/issues)
- **Repository:** [GitHub](https://github.com/StephKoenig/ComPlexionist)

---

## License

MIT License - See [LICENSE](LICENSE) for details.
