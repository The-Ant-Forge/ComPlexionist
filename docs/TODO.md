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

- [ ] Re-test removing the shutdown workaround in `src/complexionist/gui/app.py` (non-daemon watchdog timer + `os._exit(0)` after `ft.app()` returns). **Strongest lead yet (2026-08-23):** on Flet 0.86.5 the window now closes noticeably faster than on 0.85.1 in manual use. 0.86.0 replaced socket transport with an in-process `dart_bridge` FFI transport, which is exactly the layer this workaround exists to paper over. Not yet measured - confirm whether `ft.app()` now returns cleanly and whether the watchdog still fires at all. The tell is the console flash: `docs/Completed.md` (2026-07-26) records that the flash at shutdown *is* the watchdog's `taskkill`, so **no flash means the watchdog is no longer firing** and the workaround can go. Prior context: the May 0.85.1 re-test was invalid because `page.window.destroy()` is a coroutine since 0.85 and the sync close handler never awaited it; that was fixed on 2026-07-26 via `page.run_task(page.window.destroy)`.
- [ ] Declare `flet-desktop` explicitly (currently in neither `pyproject.toml` nor `uv.lock`, yet must match `flet` exactly). Two consequences: `uv sync` silently uninstalls it and breaks the exe build, and nothing but the `complexionist.spec` guard enforces the version pairing.
- [ ] CI never runs the YAML config tests - both jobs install `-e ".[dev]"`, which excludes the `yaml` extra, so `tests/test_config.py::123,155,194` skip on every run. Change to `".[dev,yaml]"`.

## Release Pipeline

- [ ] Packaged exe reports the wrong version. `_version.py` computes the version at runtime from `git rev-list --count HEAD`, which is unavailable inside a PyInstaller bundle, so every shipped exe falls back to `2.0.0` and `--version` cannot distinguish v2.0.148 from v2.0.218. `build.yml` already computes the correct value for the artifact and release names; bake it in at build time (write `_version.py` during the build, or read a `COMPLEXIONIST_VERSION` env var baked via the spec).
- [ ] Release page shows the heading twice: `build.yml` passes `body_path: RELEASE_NOTES.md` unmodified, so the `# ComPlexionist vX.Y.Z ...` line renders under the release title. Either strip the first heading line before passing it, or drop the H1 from `RELEASE_NOTES.md`. Cosmetic, and consistent across all releases so far.
- [ ] `build.yml` installs `flet-desktop` unpinned while `flet` resolves from `pyproject.toml`. They happen to match today, but the `complexionist.spec` guard hard-fails the build if they ever diverge. Pin it to the resolved `flet` version.

## Future Ideas

These were identified during code reviews but are feature work:

- Pagination for large Plex libraries (10k+ items currently loaded all at once)
- Python logging module integration instead of ad-hoc file logging
