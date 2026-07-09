# Code Review - July 2026

**Date:** 2026-07-09 | **HEAD:** `38af9e7` (commit count 153, v2.0.153-dev)
**Scope:** Full codebase per `docs/Spec-CodeReview.md` (16-item checklist) — `src/complexionist/`, `tests/`, build config, CI/CD, docs.
**Previous review:** `docs/Code-Review-2026-03-02.md` (34 commits ago).
**Suite baseline:** 270 tests collected; 269 passed, 1 skipped. Ruff clean. mypy: 2 errors (finding 31).

## Regression Check (vs March 2026 review)

**No regressions.** All spot-checked March "Done" items remain in place: dead code
(config.py functions, `PlexSeason`, mixins) has not returned; `is_date_past()` is
still the shared date utility; `PlexClient.close()` exists; dashboard uses
`show_success()`; `AppState` has no `Any` fields; stale planning docs remain deleted;
setup.py's hardened generic connection messages are intact.

**Carry-forwards:**
- **March #6 (cache helper, Skipped):** re-examined — the skip rationale still holds
  for conditional-TTL methods, but the unused helper itself should now go (finding 19)
  and a new cache-key coupling introduced by the parallel-lookup work needs a proper
  API instead (finding 26). Superseded by those two findings.
- **March #19 (CLI tests, Deferred):** still unresolved; re-raised as finding 32.
- **March #24 (path mapping complexity, Deferred):** still present in config.py, no
  new evidence of harm; recommend carrying forward as Deferred again.

**Coverage note:** March #12 hardened credential leakage in `setup.py` but the
equivalent GUI code path (`onboarding.py`) was not covered and leaks today
(finding 2) — when fixing a finding, sibling code paths should be swept too.

## Summary Table

| # | Category | Description | Action | Impact | Effort | Fix Risk | Status |
|---|----------|-------------|--------|--------|--------|----------|--------|
| 1 | Security | GUI server save bakes env-var tokens into plaintext INI | Refactor | High | M | L | Implement |
| 2 | Security | TMDB API key leaks into GUI onboarding error text | Refactor | Med | L | L | Implement |
| 3 | Security | TMDB key sent as URL query parameter | Refactor | Low | L | L | Implement |
| 4 | Supply-chain | msgpack locked at vulnerable 1.1.2 (Dependabot #7, high severity) | Add | High | L | L | Implement |
| 5 | Error handling | httpx transport errors unwrapped — one network blip aborts movie scan | Refactor | Med | L | L | Implement |
| 6 | Error handling | Malformed INI crashes GUI at startup with no message | Add | Med | L | L | Implement |
| 7 | Error handling | Per-item API failures invisible — reports silently incomplete | Add | Med | M | L | Implement |
| 8 | Error handling | `validate_config` crashes on TVDB transport error | Refactor | Low | L | L | Implement |
| 9 | Error handling | Cache corruption/write failures effectively silent | Add | Low | L | L | Implement |
| 10 | Robustness | Multi-episode parser turns `S01E01-1080p` into 1080 owned episodes | Refactor | High | L | L | Implement |
| 11 | Robustness | No guard against starting a second concurrent scan | Add | Med | L | L | Implement |
| 12 | Robustness | results.py Organize mutates UI from daemon threads; `shutil.move` killable mid-file | Refactor | Med | M | M | Implement |
| 13 | Robustness | Every scan start rewrites INI and strips all user comments | Refactor | Med | M | M | Implement |
| 14 | Robustness | Startup connection tests block the Flet event loop | Refactor | Low | L | L | Implement |
| 15 | Compatibility | Config `[options]`/`[exclusions]` wiring inconsistent between CLI/GUI; some keys inert everywhere | Refactor | High | M | M | Implement |
| 16 | Compatibility | `CACHE_VERSION` written but never read | Add | Low | L | L | Implement |
| 17 | Compatibility | pyproject version 1.2 contradicts app version 2.0; commit count trusts cwd | Refactor | Low | L | L | Implement |
| 18 | Dead code | `gui/strings.py` entirely dead (64 unused constants) | Remove | Med | L | L | Implement |
| 19 | Dead code | `cached_api_call()` helper defined/exported, never called | Remove | Med | L | L | Implement |
| 20 | Dead code | Unused client methods (`search_collection`, `search_series`, `get_series_with_episodes`) + `TVDBSeriesExtended` | Remove | Med | L | L | Implement |
| 21 | Dependencies | `python-dotenv` never imported; `.env` support claims misleading | Remove | Med | L | L | Implement |
| 22 | Dependencies | Pydantic 2.13.x deferral trigger has fired (2.13.4 stable since May) | Add | Med | L | M | Implement |
| 23 | Dependencies | `pytest-asyncio` + `asyncio_mode` carried with zero async tests | Remove | Low | L | L | Implement |
| 24 | Dependencies | Unpinned type stubs; stale "transitive via plexapi" comment on requests | Refactor | Low | L | L | Implement |
| 25 | Duplication | `OwnedMovie` list construction duplicated verbatim in movies.py | Refactor | Med | L | L | Implement |
| 26 | Duplication | `_is_movie_cached` reaches into private `_cache`, hardcodes cache-key triple | Refactor | Med | L | L | Implement |
| 27 | Duplication | Score-threshold branching ×3 (incl. unused `get_score_rating`); `media_badges` ×2 | Refactor | Low | L | L | Implement |
| 28 | Naming/consistency | Core `gaps/` imports GUI error logging → Flet import in CLI scans | Refactor | Med | M | L | Implement |
| 29 | Naming/consistency | 24h grace period and `recent_threshold_hours` express one rule in two places | Refactor | Low | L | L | Implement |
| 30 | Naming/consistency | Stale docstring describes pre-fix stagger design | Refactor | Low | L | L | Implement |
| 31 | Type safety | 2 mypy errors (`sys._MEIPASS`, unused type-ignore) | Refactor | Low | L | L | Implement |
| 32 | Test gaps | CLI tests still minimal — 6 tests vs 1,232-line cli.py (March #19) | Add | High | M | L | Implement |
| 33 | Test gaps | Parallel rate-lock branch never executed by any test (vacuous pass) | Add | Med | L | L | Implement |
| 34 | Test gaps | `utils.py` has no direct tests; movie-side grace boundary unasserted | Add | Med | L | L | Implement |
| 35 | Test gaps | Pill badge rendering has no unit test (Flet-API-breakage canary) | Add | Low | L | L | Implement |
| 36 | Docs drift | `Completed.md` has no records for any work after 2026-03-31 | Add | Med | L | L | Implement |
| 37 | Docs drift | 24h grace period undocumented (Specification.md, help screen, README) | Add | Med | L | L | Implement |
| 38 | Docs drift | CLAUDE.md/TODO.md stale: BASE_VERSION 1.1, exe ~55 MB, web-mode contradiction | Refactor | Low | L | L | Implement |
| 39 | Performance | Search rebuilds every row of both tabs on each keystroke, no debounce | Refactor | Med | L | L | Implement |
| 40 | Performance | `page.overlay` grows unboundedly (snackbars/dialogs never removed) | Refactor | Med | L | L | Implement |
| 41 | Performance | Cache file 24% larger than needed (`indent=2`) | Refactor | Low | L | L | Implement |
| 42 | Build/packaging | `upx=True` is a silent no-op locally; environment-dependent output | Refactor | Low | L | L | Implement |
| 43 | Build/packaging | pygments is both CVE floor pin and PyInstaller exclude — latent frozen-only trap | Add | Low | L | L | Implement |
| 44 | Build/packaging | 5 remaining `ft.dropdown.Option` callsites (legacy alias outside `__all__`) | Refactor | Low | L | L | Implement |
| 45 | Log quality | Background-scan crashes logged without tracebacks — undiagnosable | Add | Med | L | L | Implement |
| 46 | Log quality | Scan-error log entries lack server/library context | Add | Low | L | L | Implement |
| 47 | Log quality | Startup connection errors stored but never shown or logged | Add | Low | L | L | Implement |

---

## Triage Outcome (2026-07-09)

All 47 findings approved for implementation ("do all the recommendations").
Decision points resolved as: finding 15 — remove the inert keys
(`exclude_future`/`exclude_specials`/`tvdb.pin`) rather than wire them; wire the
GUI to `[options]`/`[exclusions]`; add `--include-specials` to `scan`.
Finding 29 — documentation half only. Finding 23 — remove despite counter-review
dissent.

**Implementation order (blast radius ascending):**
- **Wave A** — docs & metadata, no runtime code: 24, 30, 36, 37, 38, 42, 43
- **Wave B** — test additions (safety net before refactors): 32, 33, 34, 35
- **Wave C** — dead code & dead deps: 18, 19, 20, 21, 23, 25, 26, 27
- **Wave D** — targeted core fixes: 2, 3, 5, 6, 8, 9, 10, 16, 17, 28, 31, 41, 45, 46, 47
- **Wave E** — supply chain: 4, 22
- **Wave F** — GUI & behavior-visible: 1, 7, 11, 12, 13, 14, 15, 39, 40, 44
- **Final** — full verification, exe build, status updates, Completed.md record

## Detailed Findings

### Security

#### 1. GUI server save bakes env-var tokens into plaintext INI (High / M / L)
Settings' `_get_servers()` returns already-env-expanded servers (`${PLEX_TOKEN}` →
real token); `save_plex_servers()` rewrites all `[plex:N]` sections with expanded
values. Any add/edit/delete of a server via the GUI silently converts env-var
indirection into plaintext secrets on disk — a secret-handling regression path.
- **Evidence:** `src/complexionist/gui/screens/settings.py:91-94, 288-298, 342`;
  `src/complexionist/config.py:594-639` (writes raw token at 627); expansion at
  `config.py:436`.
- **Recommendation:** Round-trip raw (unexpanded) INI values — read raw sections
  with a separate parser and replace only fields the user actually edited.
- *Impact raised Med → High in counter-review adjudication (silent secret
  materialization to disk).*

#### 2. TMDB API key leaks into GUI onboarding error text (Med / L / L)
`onboarding.py`'s `_test_tmdb_connection` catches only `Timeout` before a generic
`except Exception as e: return False, f"Error: {e}"`. A `requests.ConnectionError`
message embeds the full URL including `?api_key=...`, rendered in the onboarding
error text. The CLI wizard (`setup.py`) was hardened in March; this GUI copy was not.
- **Evidence:** `src/complexionist/gui/screens/onboarding.py:62-77` (also generic
  `Error: {e}` at 51, 103) vs hardened `src/complexionist/setup.py:98-121`.
  Reproduced: connection failure yields `...url: /3/configuration?api_key=SECRETKEY123`.
- **Recommendation:** Mirror setup.py's hardening — catch `ConnectionError` with a
  generic message; never interpolate raw exceptions where the key rides in a URL.

#### 3. TMDB key sent as URL query parameter (Low / L / L)
All TMDB requests carry `api_key` in the query string, putting the key in URLs where
exceptions, proxies, and future request logging can capture it (root enabler of
finding 2). TMDB supports Bearer-token header auth.
- **Evidence:** `src/complexionist/tmdb/client.py:87`; `src/complexionist/setup.py:109`;
  `src/complexionist/gui/screens/onboarding.py:66`.
- **Recommendation:** Primary fix this cycle: apply finding 2's exception-message
  sanitization everywhere the key rides in a URL (Low effort). The full TMDB v4
  Bearer-auth migration is optional future hardening → Out of Scope list.

### Supply-chain

#### 4. msgpack locked at vulnerable 1.1.2 — Dependabot alert #7 open since June 23 (High / L / L)
msgpack ≤ 1.2.0 has a high-severity out-of-bounds read (patched in 1.2.1, advisory
published 2026-06-19). `uv.lock` resolves msgpack 1.1.2, transitive via flet 0.85.1.
The patched release is well past the 7-day cooldown — the lock simply hasn't been
refreshed, and unlike urllib3/idna, msgpack has no CVE floor pin so `uv lock --check`
passes green. This is the v2.0.145 failure mode recurring in miniature.
- **Evidence:** `uv.lock:392-394` (msgpack 1.1.2); no msgpack constraint in
  `pyproject.toml`. External data verified live during this review via
  `gh api repos/The-Ant-Forge/ComPlexionist/dependabot/alerts/7` → state `open`,
  severity `high`, patched `1.2.1`, advisory published 2026-06-19 — re-run the
  command at implementation time to confirm still current.
- **Recommendation:** Add `msgpack>=1.2.1` floor pin per the urllib3/idna precedent,
  `uv lock --upgrade-package msgpack`, verify, release. Also consider a periodic
  `gh api .../dependabot/alerts --jq '.[].state'` check in the release procedure.

### Error handling

#### 5. httpx transport errors unwrapped — one network blip aborts the movie scan (Med / L / L)
`TMDBClient.get_movie/get_collection` don't wrap `httpx.RequestError`; the ThreadPool
worker catches only `TMDBNotFoundError`/`TMDBError`, so a transient `ConnectError`
propagates through `future.result()` and kills the whole scan. The TV scan survives
the same event via its per-show catch-all — the two gap finders are inconsistent.
- **Evidence:** `src/complexionist/tmdb/client.py:114, 182`;
  `src/complexionist/gaps/movies.py:153-162, 170-172`; contrast
  `src/complexionist/gaps/episodes.py:180-185`.
- **Recommendation:** Wrap `httpx.RequestError` into `TMDBError`/`TVDBError` in
  `BaseAPIClient`; add the same per-item catch-all in `lookup_movie`.

#### 6. Malformed INI crashes GUI at startup with no user-facing message (Med / L / L)
`load_config` has no try/except around `parser.read()` (raises `configparser.Error`
on duplicate sections — a realistic hand-edit mistake) or `AppConfig.model_validate`.
GUI startup calls it unguarded and dies before any window content appears.
- **Evidence:** `src/complexionist/config.py:276-277, 430-439`;
  `src/complexionist/gui/app.py:711-716`.
- **Recommendation:** Catch parse/validation errors in `load_config`, log, and route
  to onboarding with a message naming the bad file.

#### 7. Per-item API failures invisible — reports silently incomplete (Med / M / L)
Lookups that fail after retries are logged to `complexionist_errors.log` and skipped;
neither GUI nor CLI tells the user results are partial. Thirty skipped movies look
identical to a clean scan.
- **Evidence:** `src/complexionist/gaps/movies.py:158-162, 236-247`;
  `src/complexionist/gaps/episodes.py:174-185`; no skip-count in `ScanStatistics`.
- **Recommendation:** Count skipped items in `ScanStatistics`; surface "N items could
  not be checked (see complexionist_errors.log)" in results screen / CLI summary.

#### 8. `validate_config` crashes on TVDB transport error (Low / L / L)
`TVDBClient._login` uses a bare `httpx.Client.post`; `httpx.ConnectError` is not a
`TVDBError`, so CLI `--dry-run` dies with a traceback instead of printing "Failed".
- **Evidence:** `src/complexionist/tvdb/client.py:123-142`;
  `src/complexionist/validation.py:126-132`.
- **Recommendation:** Wrap `httpx.RequestError` in `_login` as `TVDBError` (same fix
  family as finding 5).

#### 9. Cache corruption/write failures effectively silent (Low / L / L)
A corrupted cache file is discarded with no log line at all; write failures log only
at DEBUG to a logger nobody configures, so both vanish in GUI and CLI. If the file
becomes unwritable, caching silently stops persisting and every scan re-hits the APIs.
- **Evidence:** `src/complexionist/cache.py:228-231` (bare reset), `:262-269`
  (`logger.debug` only), `:45` (only stdlib-logging module in codebase, unconfigured).
- **Recommendation:** Route failures through the shared `log_error` file logging at
  WARNING; optionally a one-per-session GUI notice ("cache reset / not persisting").

### Robustness

#### 10. Multi-episode parser turns `S01E01-1080p` into 1080 owned episodes (High / L / L)
The `S(\d+)E(\d+)-(\d+)` multi-episode pattern matches resolution suffixes:
`parse_multi_episode_filename('Breaking.Bad.S01E01-1080p.mkv')` returns episodes
1–1080 as owned, silently masking every real gap in that season. No sanity bound on
range size. **Silently wrong core results.**
- **Evidence:** `src/complexionist/gaps/episodes.py:25-34, 54-67`; reproduced as above.
- **Recommendation:** Require `end >= start` and a plausible span (e.g.
  `end - start <= 20`), and/or negative lookahead for resolution tokens (`p` suffix).
  Add regression tests for `-1080p`, `-720p`, `-2160p` filenames.

#### 11. No guard against starting a second concurrent scan (Med / L / L)
The nav rail stays active during a scan; starting another spawns a second daemon scan
thread: orphaned cancellation flag, both threads writing `state` reports, duplicate
pubsub `complete` events, two `Cache()` instances racing the same file, class-level
`ScanStatistics._instance` clobbered. Leaving via nav rail also never cancels the
running scan (keeps burning API quota). Confirms the TODO.md thread-safety item —
single-scan is fine; multi-scan is the hole.
- **Evidence:** `src/complexionist/gui/app.py:238` (no guard), `:396-417`, `:636-646`;
  `src/complexionist/gui/state.py:103-108`; `src/complexionist/statistics.py:79, 84-98`.
- **Recommendation:** In `start_scan`, if `state.scan_progress.is_running`, return
  with a snackbar (or offer cancel-and-restart); keep a handle to the old
  `ScanProgress` for cancellation.

#### 12. results.py Organize mutates UI from daemon threads; `shutil.move` killable mid-file (Med / M / M)
`_run_checks`/`_do_moves` run on daemon threads and call `dialog.update()`, button
mutations, and `result_snack.update()` directly — the only screen violating the
project's own pubsub/`page.run_task` rule. `shutil.move` on a daemon thread can be
killed mid-file by the `os._exit(0)` shutdown path, leaving a partially moved file.
- **Evidence:** `src/complexionist/gui/screens/results.py:1245-1268, 1281-1327`
  (move at 1300, thread starts 1327/1330); contrast `settings.py:276-325`.
- **Recommendation:** Marshal UI updates via `page.run_task`/pubsub; make the move
  thread non-daemon or block shutdown until moves complete.

#### 13. Every scan start rewrites the INI and strips all user comments (Med / M / M)
`on_start` → `save_library_selection` does a configparser read→write round-trip of
the whole INI; configparser discards comments, so the heavily commented default
config is flattened on the very first GUI scan. `save_plex_servers` and
`_save_ignored_lists` behave the same.
- **Evidence:** `src/complexionist/gui/app.py:329-337` →
  `src/complexionist/gui/library_state.py:76-88`;
  `src/complexionist/config.py:588-630, 769-788`; template at `config.py:540-583`.
- **Recommendation:** Cheap fix: only rewrite when the selection actually changed.
  Better: comment-preserving targeted line edits. (Interacts with finding 1 — a raw
  round-trip layer solves both.)

#### 14. Startup "background" connection tests block the Flet event loop (Low / L / L)
`async_init` calls `_initialize_state()` synchronously inside a coroutine — serial
blocking network calls (up to ~30 s timeouts each) stall Python-side event handling,
despite the comment claiming background execution.
- **Evidence:** `src/complexionist/gui/app.py:693-707, 775-806`.
- **Recommendation:** `asyncio.to_thread` (or worker thread + `page.run_task`),
  matching `_on_server_changed`.

### Compatibility

#### 15. Config `[options]`/`[exclusions]` wiring inconsistent; some keys inert everywhere (High / M / M)
Same config file, different results by interface: the GUI constructs both gap finders
without `include_future`, `min_collection_size`, `min_owned`, `recent_threshold_hours`,
`include_specials`, or the `[exclusions]` lists the CLI honors (GUI effectively runs
`recent_threshold_hours=0` vs config default 24). Meanwhile `options.exclude_future` /
`options.exclude_specials` are parsed and shown by `config show` but wired to nothing
even in the CLI (flags control behavior), and `tvdb.pin` is parsed and never sent.
- **Evidence:** `src/complexionist/gui/app.py:903-908, 920-925` vs
  `src/complexionist/cli.py:600-604, 650-658, 817-822, 868-908`; inert keys:
  `src/complexionist/config.py:60, 67-68, 328, 339-340`, `cli.py:1063-1064`;
  TVDB login sends only `apikey` (`tvdb/client.py:128`). Additionally (from
  counter-review, verified): the combined `scan` command hardcodes
  `include_specials=False` when invoking the TV scan (`cli.py:1015`) and offers no
  `--include-specials` option, while the standalone `tv` command does (`cli.py:737`)
  — `scan` can never include specials.
- **Recommendation:** Pass `config.options.*`/`config.exclusions.*` into both GUI
  finders. For the inert keys: wire `exclude_*` as CLI-flag defaults or remove them
  from config/template/`config show`; remove `tvdb.pin` outright. Behavior-visible —
  decide direction in triage.

#### 16. `CACHE_VERSION` written but never read (Low / L / L)
`_empty_cache()` writes `_meta.version = 1`; `_load()` never inspects it — a future
format change cannot be detected or migrated. Confirmed lead from the review prep.
- **Evidence:** `src/complexionist/cache.py:59-60, 233-242, 210-231`.
- **Recommendation:** Check version in `_load` (mismatch → regenerate) now, while
  version 1 is the only one in the wild.

#### 17. Package metadata version contradicts app version; commit count trusts cwd (Low / L / L)
`pyproject.toml` says `version = "1.2"` while `_version.py` uses `BASE_VERSION = "2.0"`
— `importlib.metadata` reports 1.2 vs the app's 2.0.x. Also `_get_commit_count()`
runs `git rev-list` in whatever cwd the process has; run from another repo, the patch
version becomes that repo's commit count.
- **Evidence:** `pyproject.toml:7`; `src/complexionist/_version.py:15, 24-32`.
- **Recommendation:** Sync pyproject to 2.0; anchor the git call to the package's
  own directory (and/or verify the repo identity) before trusting the count.

### Dead code

#### 18. `gui/strings.py` entirely dead — 64 unused constants (Med / L / L)
The module claims to centralize all user-facing text; nothing imports it and all UI
text is hardcoded in screens. Actively misleading: implies a convention that doesn't
exist. Missed by the March review.
- **Evidence:** `src/complexionist/gui/strings.py` (whole file); zero import hits
  across `src/` and `tests/`; 64/64 constants unused.
- **Recommendation:** Delete. (Wiring it up would be feature work — localization —
  and belongs in TODO.md if wanted.)

#### 19. `cached_api_call()` helper defined and exported, never called (Med / L / L)
March #6 skipped adopting it; the helper was left behind with zero callers.
- **Evidence:** `src/complexionist/api/helpers.py:35-118`;
  `src/complexionist/api/__init__.py:10, 18`.
- **Recommendation:** Delete helper and export. Resolves the March #6 carry-forward
  (pairs with finding 26).

#### 20. Unused client methods + `TVDBSeriesExtended` (Med / L / L)
`TMDBClient.search_collection`, `TVDBClient.search_series`, and
`TVDBClient.get_series_with_episodes` have no callers. `TVDBSeriesExtended` exists
only as the uncalled method's return type plus model-only tests.
- **Evidence:** `src/complexionist/tmdb/client.py:220`;
  `src/complexionist/tvdb/client.py:304, 332`; `src/complexionist/tvdb/models.py:60`;
  `tests/test_tvdb.py:107-139`.
- **Recommendation:** Delete all three methods, the model, its export, and its
  model-only tests (no TODO.md feature needs them).

### Dead/stale dependencies

#### 21. `python-dotenv` never imported; `.env` support claims are fiction (Med / L / L)
Declared as a runtime dependency (and version-bumped in March!) but there is no
`dotenv` import anywhere. `config paths` prints a `.env` path and Specification.md
claims `.env` fallback — users are told to create a file that does nothing. Env vars
only work via `${VAR}` INI expansion reading `os.environ` directly.
- **Evidence:** `pyproject.toml:31`; zero `dotenv` grep hits in `*.py`;
  `src/complexionist/cli.py:1106`; `docs/Specification.md:210`.
- **Recommendation:** Remove the dependency, re-lock, delete the `config paths` line,
  fix Specification.md. (Alternative — actually implementing `.env` loading — is
  feature work for TODO.md.)

#### 22. Pydantic 2.13.x deferral trigger has fired (Med / L / M)
TODO.md defers until "one more point release" after 2.13.3; 2.13.4 shipped 2026-05-06
and has been stable for two months. The deferral condition is satisfied.
- **Evidence:** `docs/TODO.md:21`; uv.lock pins pydantic 2.12.5; PyPI latest 2.13.4
  (external check at review time — re-verify latest/changelog at implementation).
- **Recommendation:** Schedule the bump with explicit regression tests on cache
  hydration (`model_validate` on cached dicts) — the exact path the deferral feared.

#### 23. `pytest-asyncio` + `asyncio_mode = "auto"` with zero async tests (Low / L / L)
- **Evidence:** `pyproject.toml:47, 90-91`; no `async def`/`asyncio` in `tests/`.
- **Recommendation:** Remove both; run suite to confirm. *Counter-review dissent:
  low ROI, near-zero carry cost — a defensible Reject/Defer at triage.*

#### 24. Unpinned type stubs; stale requests comment (Low / L / L)
`types-PyYAML`/`types-requests` are the only unpinned deps; the `requests` comment
says "transitive via plexapi" but requests is now directly imported (setup.py,
onboarding.py).
- **Evidence:** `pyproject.toml:35, 50-51`; `src/complexionist/setup.py:75, 104, 130`;
  `src/complexionist/gui/screens/onboarding.py:24, 60, 86`.
- **Recommendation:** Add floor pins; reword comment ("direct import + CVE floor").

### Duplication

#### 25. `OwnedMovie` list construction duplicated verbatim (Med / L / L)
The complete-collection branch and the gap branch in movies.py build the identical
`OwnedMovie` list (same filter, same triple `tmdb_to_plex` lookups, same sort).
Introduced by the resolution/codec work (b60e568).
- **Evidence:** `src/complexionist/gaps/movies.py:270-284` vs `:308-321`.
- **Recommendation:** Extract `_build_owned_movies(...)`; collapse the triple dict
  lookup to one `.get()`.

#### 26. `_is_movie_cached` reaches into private `_cache` and hardcodes the key triple (Med / L / L)
The parallel-lookup fast path hardcodes `("tmdb", "movies", str(id))`, which must
stay in sync with `TMDBClient.get_movie`; drift would silently disable the
rate-limit skip and never be noticed.
- **Evidence:** `src/complexionist/gaps/movies.py:179-183` vs
  `src/complexionist/tmdb/client.py:106`.
- **Recommendation:** Add `TMDBClient.is_movie_cached(tmdb_id) -> bool`; the finder
  calls that. (Pairs with finding 19's helper deletion.)

#### 27. Score thresholds implemented three times; `media_badges` twice (Low / L / L)
`_get_score_color` duplicated in GUI results and CLI output with identical threshold
logic while `constants.get_score_rating()` sits unused; identical `media_badges`
property on both `OwnedMovie` and `ShowGap`.
- **Evidence:** `src/complexionist/gui/screens/results.py:158-164`;
  `src/complexionist/output/__init__.py:67-74`; `src/complexionist/constants.py:31-44`;
  `src/complexionist/gaps/models.py:32-40` vs `:323-331`.
- **Recommendation:** Both color functions map `get_score_rating()` → color (or
  delete the unused function and accept the duplication); extract a module-level
  `_media_badges(resolution, codec)` helper (do not resurrect the mixin pattern).

### Naming & consistency

#### 28. Core `gaps/` package imports GUI error logging — Flet import in CLI scans (Med / M / L)
`gaps/movies.py` (3 sites, two new since March) and `gaps/episodes.py` (2 sites)
import `log_error` from `gui.errors`, which imports Flet at module level — a pure CLI
scan that hits its first API error imports the entire Flet framework mid-scan.
- **Evidence:** `src/complexionist/gaps/movies.py:159, 238, 244`;
  `src/complexionist/gaps/episodes.py:176, 182`; `src/complexionist/gui/errors.py:11`.
- **Recommendation:** Move `log_error` file logging to a core module (e.g.
  `complexionist.errors`), re-export from `gui.errors`. TODO.md's logging-integration
  item is the fuller fix.

#### 29. 24h grace period and `recent_threshold_hours` express one rule in two places (Low / L / L)
`is_date_past()` bakes in a 24 h grace (df6100d) while `recent_threshold_hours`
(default 24) filters the same concern in `_filter_tvdb_episodes`; with defaults, any
threshold ≤ 48 h is effectively a no-op. No cross-reference exists in either place.
- **Evidence:** `src/complexionist/utils.py:13-21`;
  `src/complexionist/gaps/episodes.py:271-291`.
- **Recommendation:** Cross-reference the two in docstrings now; whether to
  consolidate into a single mechanism is a behavior decision → triage / TODO.md.

#### 30. Stale docstring describes the pre-fix stagger design (Low / L / L)
`_get_collection_ids` docstring says "slight stagger between submissions"; commit
2ebc744 replaced that with a shared rate-limit lock.
- **Evidence:** `src/complexionist/gaps/movies.py:119-120` vs `:137-151`.
- **Recommendation:** Update the docstring.

### Type safety

#### 31. Two mypy errors (Low / L / L)
(a) `config.py:135` — `sys._MEIPASS` has a ruff noqa but no mypy suppression;
(b) `results.py:1285` — `# type: ignore[arg-type]` now flagged unused because the
gui override disables arg-type while `warn_unused_ignores` is global.
- **Evidence:** `uv run mypy src/complexionist --no-error-summary` → 2 errors as above.
- **Recommendation:** `getattr(sys, "_MEIPASS")` (or targeted ignore); delete the
  stale ignore. Restores a clean informational baseline.

### Test gaps

#### 32. CLI tests still minimal — March #19, confirmed unresolved (High / M / L)
6 tests (58 lines) against 1,232-line cli.py: only `--help`, `--version`,
command-existence, `config path`. No command ever executes with mocked APIs — option
plumbing, output formats, exit codes, `cache`/`config show` all untested.
- **Evidence:** `tests/test_cli.py:11-58`; `docs/Code-Review-2026-03-02.md:29, 205-207`.
- **Recommendation:** `CliRunner` tests invoking `movies`/`tv` with mocked clients +
  temp INI: happy path per command, `--include-future`, `--recent-threshold 0`,
  missing-config error, JSON/CSV selection, non-zero exit on connection failure.

#### 33. Parallel rate-lock branch never executed by any test (Med / L / L)
The mock helper returns a bare `MagicMock()`, so `_is_movie_cached()` is always
truthy — every test, including both "parallel" tests, takes the cache-hit path and
skips the throttle (movies.py:147-151). `test_parallel_lookup_is_fast_with_cache`
passes vacuously (it never had a chance to be slow).
- **Evidence:** `src/complexionist/gaps/movies.py:146-151, 179-183`;
  `tests/test_gaps.py:364-392, 753-870`.
- **Recommendation:** Set `mock_client._cache = None` in the helper so existing tests
  exercise the throttle; add one dict-backed-fake-cache test asserting cached IDs
  skip the stagger (assert via monkeypatched `time.sleep`, not wall-clock).

#### 34. `utils.py` has no direct tests; movie-side grace boundary unasserted (Med / L / L)
No test imports `complexionist.utils` — `is_date_past()` and `retry_with_backoff()`
have zero direct tests. The grace boundary is covered for TVDB episodes but
`TMDBMovie.is_released` is only tested with 2020/2030 dates; a movie released
yesterday (the new behavior) is never asserted.
- **Evidence:** `src/complexionist/utils.py:13-72`; `tests/test_tvdb.py:54-70`;
  `tests/test_tmdb.py:87-95`.
- **Recommendation:** Add `tests/test_utils.py` (None/today/yesterday/two-days-ago;
  retry succeeds/exhausts/honors retry_after); add yesterday case to
  `test_movie_is_released`.

#### 35. Pill badge rendering has no unit test (Low / L / L)
The badge data model is well tested; the Flet rendering (`_media_badge()`) is not.
A tiny construction test would catch Flet API breakage — the class of bug behind the
v2.0.148 exe crash.
- **Evidence:** `src/complexionist/gui/screens/results.py:33, 420, 888-891`;
  model tests `tests/test_gaps.py:45-95`.
- **Recommendation:** One unit test constructing `_media_badge("1080p")` asserting
  Container/Text properties. No full screen-render tests.

### Documentation drift

#### 36. `Completed.md` has no records for any work after 2026-03-31 (Med / L / L)
Newest entry is the parallel-lookups record. Since then: pill badges (ce0113b), 24 h
grace period (df6100d), Dependabot (4b67c57), v2.0.145 lockfile-rollback remediation
(d8e33b5), exe crash fix (cedba3c) — none recorded, despite CLAUDE.md's workflow.
The CVE-rollback story currently lives only in RELEASE_NOTES.md, which is
overwritten each release.
- **Evidence:** `docs/Completed.md` top entry 2026-03-31; `git log d4b9edb..HEAD`.
- **Recommendation:** Add entries: grace period + pill badges, Dependabot adoption,
  and the v2.0.145/v2.0.148 incident (exactly the "gotcha" Completed.md exists for).

#### 37. 24 h grace period undocumented anywhere user-facing (Med / L / L)
Specification.md still says "air date > today" and doesn't mention the grace applies
to movies at all; the help screen's "missing shows/movies" troubleshooting doesn't
list the most likely new cause; README silent. Tests had to work around it with a
comment (`test_gaps.py:1510-1512`).
- **Evidence:** `docs/Specification.md:85-87`; `src/complexionist/gui/screens/help.py:179-183`;
  no "grace" hits in README.md or help.py.
- **Recommendation:** Update Specification.md filtering sections (movies + episodes,
  and that it stacks with `recent_threshold_hours`); add one help-screen
  troubleshooting bullet and a README line.

#### 38. CLAUDE.md / TODO.md stale claims (Low / L / L)
(a) CLAUDE.md versioning section says `BASE_VERSION = "1.1"`; actual is `"2.0"`.
(b) Exe size "~55 MB" vs actual 59.8 MB. (c) CLAUDE.md says web mode "not yet
implemented" and TODO.md lists it as future work, but `--web` is fully wired to
`ft.app(view=ft.AppView.WEB_BROWSER)`.
- **Evidence:** `src/complexionist/_version.py:15`; `dist/complexionist.exe`
  62,712,941 bytes; `src/complexionist/cli.py:481, 501-504`;
  `src/complexionist/gui/app.py:738-742`; `docs/TODO.md:9`.
- **Recommendation:** Fix version examples and size figure. Smoke-test `--web`; then
  either drop the TODO item and fix CLAUDE.md, or annotate both with the specific gaps.

### Performance

#### 39. Search rebuilds every row of both tabs on each keystroke (Med / L / L)
`_on_search` fires on `on_change` with no debounce and rebuilds the complete
`ExpansionTile` tree for both movie and TV lists, then full `page.update()` — per
keystroke, for hundreds of collections/shows.
- **Evidence:** `src/complexionist/gui/screens/results.py:1017-1029` → full rebuilds
  at `:390` and `:675`.
- **Recommendation:** ~250 ms debounce; rebuild only the visible tab.

#### 40. `page.overlay` grows unboundedly (Med / L / L)
Every snackbar helper appends to `page.overlay` and never removes; `ResultsScreen.build()`
appends its dialog + snackbar each build, and a new `ResultsScreen` is constructed on
every navigation. Overlay controls accumulate for the session and re-sync on each
`page.update()`.
- **Evidence:** `src/complexionist/gui/errors.py:101, 124-126, 147-149, 170-172`;
  `src/complexionist/gui/screens/results.py:1334-1336`;
  `src/complexionist/gui/app.py:297, 475, 558, 603-609`.
- **Recommendation:** Remove snackbars on dismiss (or reuse one page-level snackbar);
  guard dialog appends with an `in page.overlay` check.

#### 41. Cache file 24% larger than necessary (Low / L / L)
`indent=2` produces 29.6 MB where compact separators produce 22.5 MB (measured on the
real 9,249-entry cache). Machine-read only; still valid JSON either way — no migration.
- **Evidence:** `src/complexionist/cache.py:260, 266`; measured 0.07 s / 29.6 MB vs
  0.06 s / 22.5 MB.
- **Recommendation:** `separators=(",", ":")`, drop `indent=2`.

### Build & packaging

#### 42. `upx=True` is a silent no-op locally (Low / L / L)
UPX isn't installed locally, so PyInstaller silently skips compression — dead config
that makes exe size environment-dependent (CI with UPX would differ).
- **Evidence:** `complexionist.spec:73`; `upx` not on PATH; exe 59.8 MB.
- **Recommendation:** Set `upx=False` explicitly (reproducibility, avoids AV
  false-positive risk) — or install UPX everywhere. Update CLAUDE.md size (finding 38).

#### 43. pygments: CVE floor pin *and* PyInstaller exclude — latent frozen-only trap (Low / L / L)
Currently safe (verified: no rich module the app imports pulls pygments), but any
future use of `rich.traceback`/`rich.markdown`/`rich.syntax` works in dev and crashes
only in the frozen exe — the cedba3c failure mode.
- **Evidence:** `pyproject.toml:36` vs `complexionist.spec:54`; import verification
  negative for all used rich modules.
- **Recommendation:** Comment the exclude with why it's safe and what would break it;
  include `--cli` output paths in the post-build exe smoke test.

#### 44. Five remaining `ft.dropdown.Option` callsites (Low / L / L)
A plain alias in Flet 0.85.1 (not deprecated-wrapped), but excluded from the module's
`__all__` — legacy compat name Flet may drop. The cedba3c migration covered the other
28 module-level callsites.
- **Evidence:** `src/complexionist/gui/app.py:227, 230, 254, 275, 285`;
  flet `dropdown.py:83` (`Option = DropdownOption`).
- **Recommendation:** Migrate to `ft.DropdownOption`.

### Log quality

#### 45. Background-scan crashes logged without tracebacks (Med / L / L)
The scan thread pubsubs only `str(e)`; `log_error` writes a single line with no stack
trace. A `KeyError` mid-scan produces "Scan error: 'tmdb_id'" in both snackbar and
log — undiagnosable after the fact. (Delivery works; content is lost.)
- **Evidence:** `src/complexionist/gui/app.py:412-413`;
  `src/complexionist/gui/errors.py:24-51`.
- **Recommendation:** In `log_error`, append `traceback.format_exception(error)` to
  the file entry; keep the snackbar friendly.

#### 46. Scan-error log entries lack server/library context (Low / L / L)
Gap-finder `log_error` calls include only the item title; with multi-server,
multi-library configs the log can't say where the failing item came from.
- **Evidence:** `src/complexionist/gaps/movies.py:161, 240, 246`;
  `src/complexionist/gaps/episodes.py:178, 184`.
- **Recommendation:** Pass a context prefix (library + server) into the finder
  constructors.

#### 47. Startup connection errors stored but never shown or logged (Low / L / L)
`_initialize_state` catches exceptions into `state.connection.error_message`, which
only the settings screen's manual test reads (and overwrites). Startup failures leave
dashboard pills "disconnected" with no explanation and no log entry.
- **Evidence:** `src/complexionist/gui/app.py:771-772`; `error_message` read only in
  `settings.py:403-463`.
- **Recommendation:** `log_error(e, "Startup connection test")` in the except block;
  surface `error_message` in the dashboard status-pill tooltip.

---

## Counter-Review (Codex) — Adjudication

The draft was independently reviewed by OpenAI Codex against the codebase; its
overall verdict: "mostly strong and evidence-backed on core defects; main critique
is confidence labeling and prioritization." Disposition of its points:

- **Accepted — finding 1 impact Med → High** (silent secret materialization).
- **Accepted — finding 3 reprioritized**: message sanitization is the in-cycle fix
  (effort M → L); Bearer migration moved firmly to Out of Scope.
- **Accepted (verified) — new evidence for finding 15**: `scan` hardcodes
  `include_specials=False` with no flag (`cli.py:1015` vs `tv` at `cli.py:737`).
- **Accepted in part — external-evidence labeling** on findings 4 and 22: evidence
  now states what was verified live (gh api / PyPI) and to re-verify at
  implementation time. Finding 4 stays High — the Dependabot alert was confirmed
  via live API during this review, not assumed.
- **Rejected — finding 11 "Risk L → M"**: the column is *fix* risk (guarding
  `start_scan` is low-risk); Codex was rating the bug's severity, which Impact
  already captures. Table column renamed "Fix Risk" to prevent the same misreading.
- **Rejected as standalone finding — `os._exit(0)` shutdown**: a documented,
  deliberate Flet workaround with a tracked re-test deferral (TODO.md, commit
  bb4a67c). Its data-integrity intersection with daemon IO threads is covered by
  finding 12; noted in Audit Notes below.
- **Noted — finding 23 dissent** recorded inline for triage.

## Audit Notes (no defects — recorded for future reviews)

- **`sys.frozen`/`_MEIPASS` inventory:** exactly one divergence point —
  `config.py:110-136` (`is_frozen()`, `get_exe_directory()`, `get_assets_directory()`).
- **TODO markers:** zero TODO/FIXME/HACK/XXX in `src/` — clean.
- **Supply-chain floors:** urllib3 2.7.0, idna 3.15, requests 2.34.2, pygments 2.20.0
  all satisfy their CVE floor pins; `uv lock --check` passes under the active 7-day
  quarantine; no `[exclude-newer-package]` overrides needed anymore.
- **Cache design:** batched saves (every 250th set + flush), atomic tmp+replace
  writes, RLock coverage on all public methods — sound; serialization measured at
  0.07 s for 9,249 entries.
- **Thread discipline:** app.py, onboarding.py, settings.py all correctly marshal UI
  updates; results.py is the sole deviation (finding 12).
- **Spec excludes:** all verified absent from the runtime dependency tree; `tzdata`
  exclusion safe (no `zoneinfo` usage; all datetimes use `datetime.UTC`).
- **Flet deferrals still valid:** PyPI latest is 0.85.3 (no 0.86); the shutdown
  workaround negative finding (bb4a67c) stands.
- **`os._exit(0)` shutdown workaround (`gui/app.py:751`):** accepted lifecycle risk
  — it forcibly terminates daemon worker threads (scan, organize moves). Tracked
  for removal via the TODO.md Flet 0.86+ re-test; until then, long-running IO on
  daemon threads must tolerate hard kill (see finding 12).

## Out of Scope (belongs in TODO.md)

- **Parallelize the TV scan** — mirror movies.py's 2-worker + rate-lock pattern in
  episodes.py (Med impact, but feature-scale work with Plex-client thread-safety
  questions).
- **Consolidate grace period + `recent_threshold_hours`** into one mechanism
  (behavior change; finding 29 covers the documentation half).
- **Python `logging` integration** — already in TODO.md; findings 9/45/46/47 are the
  evidence for its priority.
- **Localization / wiring `gui/strings.py`** — only if wanted; otherwise finding 18
  deletes it.
- **TMDB v4 Bearer auth migration** — the full fix for finding 3 if more than message
  hardening is wanted.
- **Pagination for large Plex libraries** — already in TODO.md, still valid.
