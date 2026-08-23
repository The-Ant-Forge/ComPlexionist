# ComPlexionist v2.0.218 - Much Faster Scans, Flet 0.86.5

**Release Date:** August 2026
**Version:** 2.0.218

---

## Overview

This release is about speed. A movie scan that took roughly 15 minutes now
finishes in about 3.

The cause was not a lack of parallelism, which is what it looked like. Movie
lookups already ran on two worker threads, but a shared lock forced a 0.25
second gap between uncached API calls across all of them, pinning throughput at
4 requests per second no matter how many threads were running. Adding workers
would have changed nothing.

TMDB removed its 40-requests-per-10-seconds cap back in 2019 and now documents a
soft ceiling around 40 requests per second. ComPlexionist was running an order of
magnitude below it.

TV scans had the opposite problem: they were fully sequential, with no
parallelism at all.

Both are fixed, and the GUI framework moves to Flet 0.86.5, which noticeably
improves how quickly the window closes.

---

## Performance

### Movie scans: measured 4 to 18.9 requests per second

- Throttle interval reduced from 0.25s to 0.05s, worker count raised from 2 to 8
- Measured with a 200 ms simulated round trip: **4.7x faster**
- A scan that took 15 minutes should now take around 3

The rate deliberately sits at half of TMDB's documented ceiling. That budget is
per-IP, may be shared if you are behind CGNAT or a VPN, and TMDB can change it
without notice. Overshooting is survivable, since a 429 response is retried with
the server's own `Retry-After` delay, but repeated 429s would exhaust the retry
budget and end as silently skipped items. Headroom is cheap insurance against a
quietly incomplete report.

### TV scans now run in parallel

- Show analysis previously ran one show at a time with no throttling at all
- Shows are now analysed concurrently on the same worker pool
- Plex reads within each worker are serialised, because the underlying Plex
  library is not documented as thread-safe. Plex is local and fast, so this
  costs very little next to the remote TVDB calls

### Cached scans are unaffected

Cache hits skip the throttle entirely, so repeat scans of an unchanged library
were already fast and stay that way. The improvement shows up on first scans and
on newly added content.

---

## Dependencies

### Flet 0.86.5 (from 0.85.1)

The GUI framework moves up a minor version. Most of 0.86's changes target mobile
and `flet build`, neither of which applies to the Windows desktop build, but the
underlying transport between Python and the UI was rewritten. In practice the
main visible effect is that **the window now closes noticeably faster**.

### Other updates

- ruff 0.16.3, mypy 2.3.1, pyinstaller 6.22.1, setuptools 84.0.0 (development
  tooling)
- certifi, charset-normalizer, packaging, types-pyyaml refreshed
- All GitHub Actions updated to current major versions, clearing the Node 20
  deprecation warnings in CI

No known vulnerabilities across the dependency set.

---

## Fixes

### Build now bundles the correct Flet client

`complexionist.spec` selected which Flet desktop client to bundle by sorting the
cache directory names and taking the last one. That is string ordering, not
version ordering, so `0.9.0` would sort above `0.85.1`. It also picked the
newest *cached* client rather than the one actually installed.

The build now resolves the installed version explicitly and fails with a clear
message if `flet` and `flet-desktop` disagree. This mattered more than it looks:
the failure was invisible during development and would only have appeared in the
packaged executable.

### Supply-chain quarantine restored in the lockfile

An automated dependency update regenerated `uv.lock` without the 7-day package
quarantine marker. It has been restored.

---

## Testing

363 tests pass, up from 360. The three new tests cover the parallel TV path:

- Shows completing out of order are aggregated without loss or duplication
- Owned episode counts survive a TVDB lookup failure, since those files exist on
  disk regardless of whether TVDB was reachable
- Plex reads never overlap. This one was verified by deliberately removing the
  lock and confirming the test fails, rather than assuming it would catch a
  regression

Validated against a full real-world library scan: no rate-limit responses and no
skipped items.

---

## Upgrading

Replace `complexionist.exe`. Your `complexionist.ini` and cache file are not
touched, and no configuration changes are needed.

If you previously found first scans slow enough to avoid, this is the release to
retry them on.
