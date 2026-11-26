# ComPlexionist v2.0.233 - Flet 1.1, TV scan resilience

**Release Date:** November 2026
**Version:** 2.0.233

---

## Overview

A maintenance release. A TV scan no longer fails outright when a show is
removed from Plex while it runs, the GUI framework moves to Flet 1.1, and the
other dependencies are brought up to date.

No configuration changes are needed.

---

## Fixes

### A show removed mid-scan no longer aborts the TV scan

Deleting a show shortly before or during a TV scan stopped the whole scan with
a "Scan error: Show not found" message, throwing away the results for every
other show. The scan reads the list of shows first, so a show deleted before
Plex catches up is still on that list, and looking up its episodes then fails.

That show is now skipped and the scan carries on:

- **GUI:** an orange warning appears at the time, and the TV results screen
  shows a collapsed "N scan warning(s)" section under the stats line listing
  them all.
- **CLI:** warnings are printed in yellow as they happen and listed again in
  the end-of-scan summary.
- **JSON export:** gains a `warnings` list.

Only "not found" is treated this way. If the Plex server is unreachable or
rejects the token, the scan still stops, because the remaining results would
be wrong rather than one show short.

---

## Dependencies

### Flet 1.1.2 (from 1.0.4)

Flet 1.1 deprecates some text field and dropdown border settings, due for
removal in 1.3. ComPlexionist uses none of them, so no code changes were
needed.

### Other updates

- pydantic 2.14.4, click 8.5.1, markdown-it-py 4.3.0
- pytest 9.2.0, mypy 2.4.1, ruff 0.17.6 (development tooling)
- certifi, anyio and other routine patch releases

---

## Testing

374 tests pass on Python 3.11, 3.12 and 3.13, including with Flet deprecation
warnings treated as errors.

The GUI has no automated coverage. The packaged Flet 1.1.2 executable was
checked by hand.

---

## Upgrading

Replace `complexionist.exe`. Your `complexionist.ini` and cache file are not
touched.
