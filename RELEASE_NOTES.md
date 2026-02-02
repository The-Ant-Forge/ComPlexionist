# ComPlexionist v2.0.86 - Collection Folder Organization

**Release Date:** February 2026
**Version:** 2.0.86

---

## Overview

This release adds the ability to organize scattered movie files into collection folders with a single click. When movies from a collection (e.g., "Alien Collection") are spread across different folders in your library, a new "Organize" button appears to consolidate them.

---

## New Features

### Collection Folder Organization
Organize movies from a collection into a dedicated collection folder:

- **Organize Button** - Orange button appears on movie collections when files are scattered
- **Preview Dialog** - Shows current file locations and the target collection folder
- **Move Files** - One-click to move all movie files into the collection folder
- **Safety Checks** - Button disabled with explanation if:
  - Library folder is not writable
  - Duplicate filenames would conflict
  - Files already exist in target folder

### Library Locations from Plex API
- Now fetches library folder paths directly from Plex API
- Collection folder targets use the correct library root
- Works correctly with path mapping for network access

---

## Code Improvements

### Path Mapping Integration
- Organize feature respects path mapping settings
- Server paths correctly mapped to local network paths

### Better File Detection
- Checks for file existence before attempting moves
- Validates write permissions before enabling move button
- Clear error messages when issues are detected

---

## Bug Fixes

### UI Improvements
- Removed brackets from Find link on movie collection results
- Fixed process cleanup on Windows (no more orphaned processes)
- Issue text now wraps properly in organize dialog

---

## Technical Details

### Modified Files
- `src/complexionist/gui/screens/results.py` - Organize button, dialog, safety checks, move operation
- `src/complexionist/gaps/models.py` - Added `expected_folder_name`, `needs_organizing`, `collection_folder_target`, `library_locations`
- `src/complexionist/gaps/movies.py` - Pass library locations through to CollectionGap
- `src/complexionist/plex/models.py` - Added `locations` field to PlexLibrary
- `src/complexionist/plex/client.py` - Fetch library locations from Plex API
- `src/complexionist/gui/app.py` - Fixed process cleanup on window close

---

## Upgrade Notes

### From v2.0.81 or earlier
- No configuration changes needed
- Your `complexionist.ini` and cache files work without modification
- The organize feature requires path mapping to be configured if your Plex server uses different paths than your local machine

---

## Support & Contributing

- **Issues:** [GitHub Issues](https://github.com/StephKoenig/ComPlexionist/issues)
- **Repository:** [GitHub](https://github.com/StephKoenig/ComPlexionist)

---

## License

MIT License - See [LICENSE](LICENSE) for details.
