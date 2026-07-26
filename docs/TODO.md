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

- [ ] Upgrade Flet 0.85.1 → 0.86.x as a dedicated change: bump `flet` pin + matching `flet-desktop` install, re-run the app once to cache the new desktop client before building, and smoke-test the GUI end to end (dialogs, snackbars, window close, exe build). Deferred from the 2026-07-26 dependency refresh to keep it out of the dialog-lifecycle refactor's blast radius.
- [ ] Re-test removing the shutdown workaround in `src/complexionist/gui/app.py` (non-daemon watchdog timer + `os._exit(0)` after `ft.app()` returns). **New lead (2026-07-26):** the May 0.85.1 re-test was invalid — `page.window.destroy()` is a coroutine since 0.85 and the sync close handler never awaited it, so Flet's claimed destroy() fix was never actually exercised; every close rode the watchdog. Now that the handler schedules it via `page.run_task(page.window.destroy)`, re-measure whether `ft.app()` returns cleanly and the watchdog/`os._exit` can go.

## Future Ideas

These were identified during code reviews but are feature work:

- Pagination for large Plex libraries (10k+ items currently loaded all at once)
- Python logging module integration instead of ad-hoc file logging
