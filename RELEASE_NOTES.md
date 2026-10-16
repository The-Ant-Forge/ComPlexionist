# ComPlexionist v2.0.225 - Flet 1.0, clipboard and link fixes

**Release Date:** October 2026
**Version:** 2.0.225

---

## Overview

A maintenance release. The GUI framework moves to Flet 1.0, every other
dependency is brought up to date, and two GUI features that had quietly stopped
working are fixed.

No configuration changes are needed.

---

## Fixes

### Export to clipboard works again

**Copy to Clipboard** on the results screen reported nothing and copied nothing. Since the move to the
Flet 0.80 series, the clipboard has been a service that is written to
asynchronously, but the export code was still assigning text to the old
property. That assignment failed before the "copied" confirmation could appear,
so the button appeared to do nothing at all.

### Links on the Help screen open again

Clicking a link on the Help screen did nothing. Opening a URL also became an
asynchronous call in the same Flet series, and the click handler started that
call without ever running it.

Both bugs share a cause with an earlier window-close fix: a Flet function that
turns asynchronous does not raise an error when called the old way, it simply
never runs. All three call sites now schedule the work properly.

### The executable reports its real version

Every release before this one reports `2.0.0` from `--version`, whatever its
actual version. The version was worked out from git at runtime, and git is not
available inside the packaged executable. It is now stamped in at build time, so
this release reports `2.0.225`.

### Release page titles

Release titles on GitHub now carry a short summary, and the heading no longer
appears twice on the release page.

---

## Dependencies

### Flet 1.0.4 (from 0.86.5)

Flet 1.0 removes every API that was deprecated during the 0.80 series.
ComPlexionist used four of them, and they have been replaced with their
current equivalents. Nothing should look different: the button change in
particular is a rename of the same control.

1.0.4 was chosen over 1.0.0 deliberately. Four point releases followed 1.0.0
within a month, several fixing event handling and Windows desktop issues.

### Other updates

- pydantic 2.14.0, plexapi 4.18.3, click 8.5.0
- urllib3 2.8.0, idna 3.20, msgpack 1.2.3, pygments 2.21.0 (all carry security
  floors in the project, now well above them)
- pyinstaller 6.22.3, mypy 2.4.0, ruff 0.16.10 (development tooling)
- oauthlib 4.0.0, pulled in by Flet. ComPlexionist does not use it

No known vulnerabilities across the dependency set.

---

## Testing

365 tests pass on Python 3.11, 3.12 and 3.13, including with deprecation
warnings treated as errors.

The two fixes above are in the GUI, which has no automated test coverage. They
were verified by hand on the packaged Flet 1.0.4 executable, along with
onboarding, settings, the results screen and closing the window.

---

## Upgrading

Replace `complexionist.exe`. Your `complexionist.ini` and cache file are not
touched.
