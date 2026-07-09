# ComPlexionist v2.0.199 - Scan Accuracy, Security Hardening & Code Consolidation

**Release Date:** July 2026
**Version:** 2.0.199

---

## Overview

This release implements all 47 findings from the July 2026 code consolidation
review (`docs/Code-Review-2026-07.md`) — a full-codebase audit covering
correctness, security, supply chain, robustness, tests, and documentation,
independently counter-reviewed before implementation. The headline items:

1. **A scan-accuracy bug is fixed**: filenames like `Show.S01E01-1080p.mkv`
   were parsed as a multi-episode range covering episodes 1–1080, silently
   marking entire seasons as owned and hiding real gaps.
2. **GUI and CLI scans now produce the same results** from the same config —
   the GUI previously ignored the `[options]` and `[exclusions]` sections.
3. **A high-severity dependency vulnerability is patched** (msgpack) and both
   it and Pydantic are floor-pinned so lockfile re-resolution can never
   silently roll them back (the v2.0.145 lesson, now enforced by policy).

The test suite grew from 270 to 360 tests, and the exe is ~4 MB smaller after
dead-dependency removal.

---

## Bug Fixes

### Multi-episode filename parsing (scan accuracy)
- `S01E01-1080p`-style filenames matched the multi-episode range pattern
  (`S01E01-02`), producing an owned range of episodes 1 through 1080 and
  masking every real gap in that season
- Range ends followed by a resolution token are now rejected, ranges must be
  ascending, and a sanity cap of 20 episodes per multi-episode file applies
- Legitimate multi-episode files (`S01E01-02`, `S01E01-E03`) parse as before

### GUI scans now honor your config file
- The GUI constructed its gap finders with hardcoded defaults, ignoring
  `recent_threshold_hours`, `min_collection_size`, `min_owned`, and the entire
  `[exclusions]` section that the CLI honors
- GUI and CLI scans of the same library now return the same results
- Note: your first GUI scan after upgrading may show fewer items than before —
  that's your exclusions and the 24-hour recent threshold being applied for
  the first time

### Network resilience during movie scans
- A single transient network error (connection reset, DNS blip) during a
  parallel TMDB lookup aborted the entire movie scan; TV scans survived the
  same event. Transport errors are now wrapped and handled per-item in both
  scan types — the affected item is skipped and logged, the scan continues
- `--dry-run` connection validation no longer prints a raw traceback when the
  TVDB API is unreachable

### Startup and lifecycle
- A malformed `complexionist.ini` (e.g. a duplicated section from hand-editing)
  crashed the GUI before any window appeared; it now routes to onboarding with
  a message naming the problem file
- Startup connection tests no longer block the UI — the window appears
  immediately even when a configured server is unreachable
- Starting a scan while one is already running now shows a warning instead of
  spawning a second concurrent scan (which corrupted progress and statistics)
- File moves from the Organize feature are completed (with a timeout) before
  the app exits, instead of being killable mid-move at window close

---

## Security Fixes

### msgpack — High severity (Dependabot alert #7)
- Out-of-bounds read / crash on `Unpacker` reuse after a caught error
- Transitive dependency via Flet; upgraded **1.1.2 → 1.2.1**
- Floor pin `msgpack>=1.2.1` added to `pyproject.toml` per the CVE-pin policy
  introduced after the v2.0.145 lockfile-rollback incident

### API keys no longer shown on screen in error messages
- The GUI onboarding connection tests interpolated raw exception text into the
  on-screen error message; a connection failure could display the full request
  URL including `?api_key=...`. All onboarding tests now use the same
  sanitized, generic messages as the CLI setup wizard (hardened in March)

### GUI edits no longer write secrets into your config file
- Editing/adding/deleting a Plex server in Settings rewrote the entire INI
  with env-expanded values — silently converting `${PLEX_TOKEN}`-style
  indirection into plaintext tokens on disk, and stripping every comment
- A new raw INI editor preserves comments, ordering, and unexpanded `${VAR}`
  references; only fields you actually edit are rewritten, and unchanged
  library selections skip the write entirely
- Known limitation: a legacy single-`[plex]` section being migrated to the
  `[plex:0]` format by a GUI edit still writes literal values (tracked in
  `docs/TODO.md`)

---

## Improvements

### Scan transparency
- If items couldn't be checked (network errors, missing API data), the results
  screen and CLI summary now say so: "N item(s) could not be checked (see
  complexionist_errors.log)" — previously a partial scan looked identical to a
  clean one
- The error log now includes full tracebacks and library/server context for
  each failure, making multi-server issues diagnosable after the fact
- Cache corruption or write failures are logged (previously silent) — a cache
  that stops persisting no longer degrades scans invisibly

### Performance & UI
- Results search is debounced (250 ms) and rebuilds only the visible tab —
  typing in large libraries no longer rebuilds every row of both tabs per
  keystroke
- Snackbars and dialogs are cleaned from the page overlay after use instead of
  accumulating for the session
- The cache file is written as compact JSON (~24% smaller on disk); cache
  format version is now checked on load with clean regeneration on mismatch

### CLI
- `scan` gained `--include-specials` (previously hardcoded off, unlike the
  standalone `tv` command)
- Inert config keys removed: `tvdb.pin`, `options.exclude_future`, and
  `options.exclude_specials` were parsed and displayed but wired to nothing.
  Existing config files containing them keep working (unknown keys are
  ignored); behavior is controlled by the `--include-future` /
  `--include-specials` flags. The decorative (non-functional) Exclude
  Future/Specials switches were removed from GUI Settings for the same reason

### Codebase consolidation (developer-facing)
- Dead code removed: the unused `gui/strings.py` module, three unused API
  client methods, the unused `cached_api_call` helper
- Dependencies removed: `python-dotenv` (declared but never imported — the
  documented `.env` support never existed; use `${VAR}` references in the INI
  instead) and `pytest-asyncio` (no async tests)
- Core scan code no longer imports the Flet GUI framework for error logging in
  CLI mode; mypy baseline restored to clean; package metadata version synced
  to 2.0
- Test suite: 270 → 360 tests, including CLI command tests with mocked APIs,
  direct tests for the grace-period date logic, and deterministic tests for
  the parallel-lookup rate limiter (which previous tests never actually
  exercised)

### Dependencies
- **msgpack 1.1.2 → 1.2.1** (security, floor-pinned)
- **pydantic 2.12.5 → 2.13.4** (floor-pinned; cache-hydration regression that
  deferred this upgrade was fixed upstream in 2.13.4)
- Removed: python-dotenv, pytest-asyncio

---

## Upgrade Notes

- **Scan results may legitimately change**: the episode parser fix can reveal
  gaps that were previously hidden by misparsed filenames, and GUI scans now
  apply your configured exclusions and recent-content threshold
- Config files are fully compatible; removed keys are ignored if present
- Cache files from previous versions remain compatible (same format version);
  the file will shrink on first write due to compact serialization
- No action needed for the msgpack/Pydantic upgrades — they're bundled

---

## Support & Contributing

- **Issues:** [GitHub Issues](https://github.com/The-Ant-Forge/ComPlexionist/issues)
- **Repository:** [GitHub](https://github.com/The-Ant-Forge/ComPlexionist)

---

## License

MIT License - See [LICENSE](LICENSE) for details.
