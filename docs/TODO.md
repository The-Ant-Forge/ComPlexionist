# ComPlexionist - Development TODO

Forward-looking work items only. See `Completed.md` for the durable record of finished work.

---

## GUI Enhancements

- [ ] Legacy single-`[plex]` INI migration: a GUI server edit migrates it to `[plex:0]` with literal (env-expanded) values — extend the raw INI editor to preserve `${VAR}` tokens in that one migration path too (July 2026 review, findings 1+13 known limitation)

- [ ] Local web mode (`complexionist --web` opens browser) — wired via `ft.AppView.WEB_BROWSER`; needs verification + polish
- [ ] Keyboard shortcuts for common actions
- [ ] Thread safety for AppState updates from background scan threads (add locks or use queue)
- [ ] Config hot-reload (detect INI file changes while app is running)
- [ ] `ScanRunner` abstraction for scan execution (deferred — higher risk, moderate value)

## Documentation

- [ ] API key setup instructions (standalone guide for Plex token, TMDB, TVDB)

## Dependency Maintenance

- [ ] Re-test removing the shutdown workaround in `src/complexionist/gui/app.py` (non-daemon watchdog timer + `os._exit(0)` after `ft.app()` returns) when Flet 0.86+ ships. Tested with 0.85.1 (May 2026): close still hangs despite the 0.85.0 release notes claiming a fix for the `page.window.destroy()` hang with `prevent_close=True` on Windows. Likely cause: our `FLET_APP_HIDDEN` startup + pubsub subscription + background scan thread combination prevents clean `ft.app()` return regardless of the destroy() fix.

## Future Ideas

These were identified during code reviews but are feature work:

- Pagination for large Plex libraries (10k+ items currently loaded all at once)
- Python logging module integration instead of ad-hoc file logging
