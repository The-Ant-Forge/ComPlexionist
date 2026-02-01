# ComPlexionist v2.0.80 - Help Screen & Reliability Improvements

**Release Date:** February 2026
**Version:** 2.0.79

---

## Overview

This release adds an in-app Help screen with a comprehensive user guide, improves error handling and logging, and enhances startup performance. The application is now more resilient when encountering API errors during scans.

---

## New Features

### Help Screen with Embedded User Guide
A complete help system accessible directly from the navigation rail:

- **Getting Started** - Setup wizard walkthrough, where to get API keys
- **Running Scans** - Scan types, progress screen, cancellation
- **Understanding Results** - Completion scores, movie collections, TV seasons
- **Exporting** - CSV, JSON, and clipboard options
- **Settings & Configuration** - Config location, exclusions, cache management
- **Troubleshooting** - Common errors, log file location

The Help screen uses GitHub-flavored Markdown rendering with clickable links that open in your browser. Version number displayed in the header for easy reference.

### UI Tooltips
Added helpful tooltips throughout the interface:

- **Status badges** - Hover over Plex/TMDB/TVDB indicators to see connection status details
- **Quick Actions** - Settings and Clear Cache buttons now have descriptive tooltips

---

## Improvements

### Error Logging
- All errors are now logged to `complexionist_errors.log` in the application folder
- Log entries include timestamp, error type, and context
- Useful for debugging API issues or reporting bugs

### Persistent Error Messages
- Error snackbars now stay visible until dismissed (no auto-hide)
- Click "Dismiss" to close error messages
- Ensures users don't miss important error information

### Resilient Scan Handling
- Scans now continue when individual shows/collections encounter API errors
- Errors are logged and the scan proceeds to the next item
- No more full scan failures due to a single problematic item

### TVDB API Robustness
- Fixed parsing error when TVDB returns `null` for series name
- Handles malformed API responses gracefully (e.g., "Bob's Burgers" edge case)

### Faster Startup
- Deferred module initialization for quicker window appearance
- Window stays hidden until fully loaded (no flash of empty window)
- Connection tests run in background after UI is visible

### Settings Display Fix
- Cache section now shows correct file path
- Fixed display issues in settings panel

---

## Developer/CI Improvements

### Python 3.13 Support
- Added Python 3.13 to CI test matrix
- All tests pass on Python 3.11, 3.12, and 3.13

### Faster CI Builds
- Switched to `uv` for dependency installation
- Significantly faster test runs in GitHub Actions

### Updated Dependencies
- All dependencies updated to latest compatible versions

---

## Bug Fixes

- Fixed unused import warnings (cleaner codebase)
- Fixed library selection dialog focus (no more double-clicking needed)
- Fixed flaky test in CI

---

## Technical Details

### New Files
```
src/complexionist/gui/screens/help.py  # Help screen with embedded guide
```

### Modified Files
- `app.py` - Help navigation, improved scan error handling
- `dashboard.py` - Tooltips on status badges and buttons
- `state.py` - Added HELP screen enum
- `errors.py` - Error logging, persistent snackbars
- `gaps/episodes.py` - Resilient error handling in TV scans
- `gaps/movies.py` - Resilient error handling in movie scans
- `tvdb/models.py` - Optional name field for robustness

---

## Upgrade Notes

### From v2.0.65 or earlier
- No configuration changes needed
- Your `complexionist.ini` and cache files work without modification
- New error log file will be created automatically when errors occur

---

## Commits Since v2.0.65

- Add Help screen with embedded user guide and UI tooltips
- Add error logging, persistent snackbars, and resilient scan handling
- Improve startup and exit behavior, fix settings display
- Fix TVDB model to handle null series names
- CI: Use uv for faster installs, add Python 3.13 to test matrix
- Update dependencies to latest versions
- Defer initialization for faster startup

---

## Support & Contributing

- **Issues:** [GitHub Issues](https://github.com/StephKoenig/ComPlexionist/issues)
- **Repository:** [GitHub](https://github.com/StephKoenig/ComPlexionist)

---

## License

MIT License - See [LICENSE](LICENSE) for details.
