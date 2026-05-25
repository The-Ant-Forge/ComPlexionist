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

## Dependency Maintenance

- [ ] Upgrade Pydantic to 2.13.x (target 2.13.5+ or 2.14 stable). v2.13.0 had `ValidationInfo.data` / `field_name` regressions inside `model_validate_json()` that took two patches to resolve (2.13.3). Waiting for one more point release before bumping, since this is exactly the path our cache hydration uses.
- [ ] After Flet 0.85.1 proves stable in production, evaluate removing the shutdown workaround in `src/complexionist/gui/app.py` (non-daemon watchdog timer + `os._exit(0)` after `ft.app()` returns). Flet 0.85.0 fixed the underlying `page.window.destroy()` multi-second hang with `prevent_close=True` on Windows.

## Future Ideas

These were identified during code reviews but are feature work:

- Pagination for large Plex libraries (10k+ items currently loaded all at once)
- Python logging module integration instead of ad-hoc file logging
