# ComPlexionist v2.0.88 - Robustness & Performance

**Release Date:** February 2026
**Version:** 2.0.88

---

## Overview

This release adds new features for organizing your media, shows TV series status indicators, dramatically improves caching for ended shows, and addresses findings from a comprehensive code review — improving thread safety, reducing code duplication, and optimizing the executable size.

---

## New Features

### Collection Folder Organization
Organize movies from a collection into a dedicated collection folder:
- **Organize Button** - Orange button appears on movie collections when files are scattered
- **Preview Dialog** - Shows current file locations and the target collection folder
- **Move Files** - One-click to move all movie files into the collection folder
- **Safety Checks** - Button disabled with explanation if library folder is not writable, duplicate filenames would conflict, or files already exist in target folder

### Open Media Folder from Results
- **Folder Button** - Opens the local folder containing your media files directly from results
- **Path Mapping** - Configure Plex-to-local path mapping for NAS/network access in Settings

### TV Show Status Indicator
- Shows "Continuing", "Ended", "Cancelled" etc. as a colored chip next to each TV show in results
- Helps you decide whether to pursue missing episodes

### Smart Cache TTLs for Ended Shows
- Ended/cancelled TV shows are now cached for **1 year** (vs 24 hours for continuing shows)
- Series info for ended shows also cached for 1 year (vs 7 days)
- Dramatically reduces API calls on subsequent scans for large TV libraries

---

## Improvements

### Code Architecture
- **BaseAPIClient** - Extracted shared base class for TMDB/TVDB clients, eliminating ~150 lines of duplicated response handling, error mapping, date parsing, and cache tracking
- **Shared UI Builders** - Extracted 7 shared methods from the results screen, reducing movie/TV display duplication by ~300 lines
- **YAML Config Error Handling** - Graceful fallback on malformed YAML config files instead of crash

### Stability & Performance
- **Thread-Safe Cache** - Added `threading.RLock` to all cache operations, preventing race conditions if concurrent access occurs
- **Atomic Cache Saves** - Cache now writes to a `.tmp` file first, then renames — prevents data corruption on disk errors
- **Idle-Time Cache Cleanup** - Expired cache entries are pruned automatically after each scan completes
- **Optimized Executable** - Reduced from ~92 MB to ~55 MB by excluding unused transitive dependencies (numpy, pandas, matplotlib, pygments) and bundling flet_desktop properly

### Build System
- **Committed Spec File** - `complexionist.spec` now contains all build configuration (excludes, dynamic package paths, flet_desktop bundling)
- **Simplified CI** - Build workflow now runs `pyinstaller complexionist.spec` directly instead of the previous flet pack + sed patching approach

---

## Bug Fixes

- Fixed orphaned processes on Windows when closing the GUI
- Fixed Clear Cache button not working on the dashboard
- Fixed TV show ignore button error handling
- Tightened `pytest-asyncio` dependency pin to `>=0.26.0` (prevents async mode configuration issues)

---

## Upgrade Notes

### From v2.0.81 or earlier
- No configuration changes needed
- Your `complexionist.ini` and cache files work without modification
- The cache will automatically benefit from longer TTLs for ended shows on next scan
- Configure path mapping in Settings if using network/NAS storage

---

## Support & Contributing

- **Issues:** [GitHub Issues](https://github.com/StephKoenig/ComPlexionist/issues)
- **Repository:** [GitHub](https://github.com/StephKoenig/ComPlexionist)

---

## License

MIT License - See [LICENSE](LICENSE) for details.
