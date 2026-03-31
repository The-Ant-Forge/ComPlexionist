# ComPlexionist - Development TODO

Forward-looking work items only. See `Completed.md` for the durable record of finished work.

---

## GUI Enhancements

- [ ] Local web mode (`complexionist --web` opens browser)
- [ ] Keyboard shortcuts for common actions
- [ ] Thread safety for AppState updates from background scan threads (add locks or use queue)
- [ ] Config hot-reload (detect INI file changes while app is running)
- [ ] `ScanRunner` abstraction for scan execution (deferred — higher risk, moderate value)

## Documentation

- [ ] API key setup instructions (standalone guide for Plex token, TMDB, TVDB)

## Future Ideas

These were identified during code reviews but are feature work:

- Parallel TMDB collection lookups using ThreadPoolExecutor for large libraries
- Pagination for large Plex libraries (10k+ items currently loaded all at once)
- Python logging module integration instead of ad-hoc file logging
