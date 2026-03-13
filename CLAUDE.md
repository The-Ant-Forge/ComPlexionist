# Agent Notes (ComPlexionist)

This file is agent-facing documentation for working on **ComPlexionist**. It focuses on:
- project orientation (what it is and how it's built)
- local development on Windows
- how we collaborate (TODO workflow, completed-work record, commits, PRs, releases)

This doc is intentionally pragmatic: it should be enough for an agent joining cold to build, test, diagnose, and ship changes without guesswork.

---

## Project basics

- **Purpose:** Find missing movies in Plex collections and missing TV episodes in series
- **Build system:** Python with `uv` (pyproject.toml, src layout)
- **Primary target OS:** Windows (development), cross-platform target
- **Language:** Python 3.11+
- **Package name:** `complexionist`

Key files:
- `README.md` — project overview
- `docs/Plex-Background.md` — Plex API research and technical background
- `docs/Specification.md` — detailed feature specs and architecture
- `docs/TODO.md` — forward-looking work items
- `docs/Completed.md` — durable record of finished work
- `pyproject.toml` — project configuration, dependencies, entry points
- `src/complexionist/` — main package source code
- `tests/` — pytest test suite

---

## External APIs and Dependencies

### Plex Media Server
- **Authentication:** X-Plex-Token (header or URL parameter)
- **Base URL:** `http://[PMS_IP]:32400`
- **Key library:** [python-plexapi](https://github.com/pkkid/python-plexapi)

### TMDB (The Movie Database)
- **Purpose:** Get complete movie collection data
- **API:** `https://api.themoviedb.org/3/`
- **Auth:** API key required (free tier available)

### TVDB (TheTVDB)
- **Purpose:** Get complete TV episode listings
- **API:** `https://api4.thetvdb.com/v4/`
- **Auth:** API key required

---

## GUI Module (Flet)

The GUI is built with [Flet](https://flet.dev/) (Python framework based on Flutter).

### Key Patterns

**Flet 0.80+ API changes:**
- Event handlers set as properties: `control.on_click = handler` (not constructor args)
- Dialog management: `page.show_dialog(dialog)`, `dialog.open = False`
- Window events: `page.window.on_event`, async handlers for close
- Clipboard: `page.clipboard = text` (property assignment, not method call)
- Snackbar: `page.overlay.append(snack); snack.open = True; page.update()` (NOT `page.open()`)

**Thread-safe UI updates:**
- Background scan runs in `threading.Thread`
- Progress sent via `page.pubsub.send_all({...})`
- Main thread subscribes with `page.pubsub.subscribe(handler)`
- Never call `page.update()` directly from background thread

**State management:**
- All state in `AppState` dataclass (state.py)
- Screens receive state reference, read/write as needed
- `scanning_screen` reference stored for progress updates

### Running the GUI
```bash
# Desktop window mode (default behavior)
uv run complexionist
# or explicitly:
uv run complexionist --gui

# CLI mode (command-line interface)
uv run complexionist --cli

# Web browser mode (not yet implemented)
uv run complexionist --web
```

---

## Local development environment (Windows)

### Shells you can use
- **PowerShell**: recommended for interactive Windows work
- **Git Bash / sh**: works fine for Python and git commands

### Prerequisites
- **Git**
- **Python 3.11+**
- **uv** (recommended) or pip for package management

### Setup
```bash
# Create virtual environment and install dependencies
uv venv
uv pip install -e ".[dev]"

# Or with pip
python -m venv .venv
.venv\Scripts\activate
pip install -e ".[dev]"
```

### Common local commands (repo root)
```bash
# Run tests
uv run pytest tests/ -v

# Run linting
uv run ruff check src tests

# Auto-fix lint issues
uv run ruff check --fix src tests

# Type checking (informational)
uv run mypy src/complexionist --no-error-summary

# Run the GUI (default mode)
uv run complexionist

# Run the CLI
uv run complexionist --cli --help
uv run complexionist movies --help
uv run complexionist tv --help
uv run complexionist config show
uv run complexionist cache stats
```

### Configuration (complexionist.ini)
```ini
[plex:0]
name = Main Server
url = http://your-plex-server:32400
token = your-plex-token

# Additional servers use incrementing indices:
# [plex:1]
# name = 4K Server
# url = http://your-4k-server:32400
# token = your-4k-token

[tmdb]
api_key = your-tmdb-api-key

[tvdb]
api_key = your-tvdb-api-key
```

Config file is searched in: exe directory → current directory → `~/.complexionist/`

---

## Working style (how we operate)

### Keep diffs focused
- Avoid unrelated reformatting.
- Avoid line-ending churn on Windows.
- One logical change per commit.

### Planning sessions → write a spec
Whenever we do a planning session (plan mode), always write the finalised specification into `docs/` as a named document (e.g., `docs/countdown timer spec.md`). This ensures we have a durable reference if context is lost or the session is interrupted.

### Compile/test locally after changes
Preferred loop:
1. Make a small, targeted change.
2. Run tests/linting after each change.
3. Only then commit/push.

---

## Pre-commit checks (REQUIRED)

```bash
# Check (required before every commit):
uv run ruff check src tests && uv run ruff format --check src tests

# Auto-fix if checks fail:
uv run ruff check --fix src tests && uv run ruff format src tests

# MyPy (optional — informational in CI, pre-existing errors exist):
uv run mypy src/complexionist --ignore-missing-imports
```

After changes, also check if `docs/Specification.md`, `README.md` need updating and whether `docs/TODO.md` items can be moved to `docs/Completed.md`.

---

## TODO + Completed workflow (docs-driven)

This repo keeps:
- **future work** in `docs/TODO.md`, and
- a durable **completed-work record** in `docs/Completed.md`.

This avoids `docs/TODO.md` turning into a changelog while still preserving engineering context (what shipped, why it mattered, and where it lives).

When implementing an item from `docs/TODO.md`:
1. **Do the implementation first**, including tests.
2. **Update `docs/TODO.md` (future only)**:
   - Move completed items out.
   - Add/adjust any new items discovered during the work.
   - Keep the file focused on *forward-looking* items.
3. **Add a record to `docs/Completed.md`**:
   - Title, Why, Where (key files/classes), What we did.
   - Capture important assumptions/gotchas.
4. **Clean up in-code TODO comments**:
   - Remove TODOs that are now addressed.
5. **Prefer small commits**:
   - Ideally: one commit per focused TODO item.

Goal: keep code clean, keep `docs/TODO.md` as the single source of truth for future work, and keep `docs/Completed.md` as the durable record of finished work.

---

## Git workflow (commit and push)

Common sequence:
```bash
# 1. Run pre-commit checks FIRST
uv run ruff check src tests && uv run ruff format --check src tests

# 2. Review changes
git status
git diff

# 3. Stage and commit
git add <specific-files>
git commit -m "Meaningful summary of change"

# 4. Push
git push
```

Prefer adding specific files over `git add -A` to avoid accidentally committing sensitive files.

This repo's current working mode is to commit and push directly to `main` (after local verification).
If you need review/approval or want to isolate risk, create a PR instead:
```
gh pr create --fill
gh pr view --web
```

---

## CI/CD Workflows

| Workflow | File | Trigger | Purpose |
|----------|------|---------|---------|
| Python | `.github/workflows/ci.yml` | Push/PR to main | Tests (3.11, 3.12), ruff, mypy |
| Windows | `.github/workflows/build.yml` | Push tag `v*` | PyInstaller exe → GitHub Release |

The build workflow creates a GitHub Release with `RELEASE_NOTES.md` as the body and `complexionist.exe` attached.

```bash
gh run list --branch main --limit 5   # check CI status
gh run watch --exit-status             # watch a run
gh run view --log-failed               # diagnose failures
```

---

## Local Exe Build

Build a Windows executable locally for testing before creating a release.

### Prerequisites
Flet CLI is included as a dependency. PyInstaller is included in dev dependencies.

### Build command

The committed `complexionist.spec` handles dynamic package paths, flet_desktop bundling, all excludes, and icon embedding.

```bash
# IMPORTANT: pyinstaller clears dist/, which deletes your test config/cache!
# Backup → build → restore:
mkdir -p /tmp/complexionist-backup
cp dist/complexionist.ini dist/complexionist.cache.json /tmp/complexionist-backup/ 2>/dev/null || true
uv run pyinstaller complexionist.spec --noconfirm
cp /tmp/complexionist-backup/complexionist.ini /tmp/complexionist-backup/complexionist.cache.json dist/ 2>/dev/null || true
```

The exe looks for `complexionist.ini` and `complexionist.cache.json` in its own directory first, making dist/ a self-contained test environment.

### Output
- Executable: `dist/complexionist.exe` (~55 MB)
- Build artifacts: `build/` (gitignored)

### Verify the build
```bash
# Test CLI mode
dist/complexionist.exe --version
dist/complexionist.exe --cli --help

# Test GUI mode (default)
dist/complexionist.exe
```

### When to build locally
Build an exe for testing after making code changes to:
- `src/complexionist/**/*.py` - Any Python source files
- `pyproject.toml` - Dependencies or entry points

No need to rebuild for:
- `docs/**` - Documentation only
- `tests/**` - Test files only
- `README.md`, `agents.md` - Markdown files
- `.github/**` - CI/CD configuration

**IMPORTANT:** After completing any code changes, always build the exe so the user can test. Don't wait to be asked - build proactively when implementation is done.

---

## Versioning

### Format: `MAJOR.MINOR.{commit_count}`

Example: `1.1.15` where:
- `1.1` = Base version (manually controlled in `src/complexionist/_version.py`)
- `15` = Auto-calculated from `git rev-list --count HEAD`

### How it works

1. Base version stored in `src/complexionist/_version.py` as `BASE_VERSION = "1.1"`
2. At runtime, `_get_commit_count()` runs `git rev-list --count HEAD`
3. Full version = `{BASE_VERSION}.{commit_count}`
4. Falls back to `{BASE_VERSION}.0` if git unavailable (e.g., in packaged exe)

### When to bump base version

- **Patch (third number):** Automatic via commit count
- **Minor (second number):** New features, edit `BASE_VERSION` in `_version.py`
- **Major (first number):** Breaking changes, edit `BASE_VERSION` in `_version.py`

---

## Release Procedure

1. **Verify CI passing:** `gh run list --branch main --limit 1`
2. **Check version:** `git rev-list --count HEAD` → version will be `{BASE_VERSION}.{count}`
3. **Update `RELEASE_NOTES.md`** — version, date, features, changes
4. **Update help screen** — check `src/complexionist/gui/screens/help.py` matches new features
5. **Commit** all updates before tagging
6. **Tag and push:**
   ```bash
   git tag -a v1.1.15 -m "Release v1.1.15"
   git push origin v1.1.15
   ```
7. **Monitor:** `gh run watch --exit-status`
8. **Verify:** `gh release view v1.1.15`

---

## Release Notes (`RELEASE_NOTES.md`)

`RELEASE_NOTES.md` at repo root is used as the GitHub Release body. Follow the existing format when updating. The build workflow automatically uses it — no manual copy needed.

**Tip:** The GitHub Release title duplicates the first headline, so the build workflow strips it. No action needed.

---

## Repository hygiene / gotchas

- **Line endings:** Windows checkouts may flip LF/CRLF depending on Git settings. Avoid churn by not reformatting unrelated files.
- **Secrets:** Never commit API keys or tokens. Use a `complexionist.ini` file (gitignored).
- **Generated outputs:** `build/`, `dist/`, `__pycache__/`, `.venv/` should not be committed.
- **`docs/`** is tracked and intended for specs/planning.

---

## When diagnosing issues

CI failures:
- use `gh run view --log-failed` to quickly see why a run failed
- confirm the run corresponds to the commit SHA you expect

### Debugging workflow hygiene (temporary changes)
When investigating a bug:
- Do **not** commit/push debug-only changes unless explicitly requested.
- Keep temporary debug instrumentation local until you've identified the root cause.
- If a temporary diagnostic ends up being genuinely useful long-term, keep it — but make it intentional.


## Code Consolidation Reviews

Periodic reviews to ensure code hygiene after significant changes.

### When to trigger
- After ~30+ commits since the last review
- Before a major release
- After large feature work or dependency upgrades
- If it's been 6+ weeks since the last review

### Scope
All source code, tests, build configuration, CI/CD, and project metadata.

### Review Checklist

**Correctness & safety (review first):**
1. **Security** — input validation gaps, credential handling, OWASP patterns
2. **Error handling** — inconsistent patterns, swallowed exceptions, missing
   user-facing messages
3. **Robustness** — race conditions, resource leaks, missing cleanup
4. **Compatibility** — CLI argument/flag changes, config schema changes,
   cache/data format migration, breaking changes to public interfaces

**Code quality:**
5. **Dead code** — unused functions, classes, modules, imports, config keys
6. **Dead/stale dependencies** — unused libraries, outdated packages with
   known CVEs, license concerns, or unmaintained status
7. **Duplication** — repeated or near-identical logic that should be shared
8. **Naming & consistency** — mixed conventions, unclear names, stale comments
9. **Type safety** — missing annotations, `Any` overuse, type errors

**Testing & docs:**
10. **Test gaps** — untested code paths, stale tests, missing edge cases
11. **Documentation drift** — specs, docstrings, or README sections that no
    longer match the code

**Efficiency:**
12. **Performance** — unnecessary work, avoidable allocations, slow patterns
13. **Build & packaging** — PyInstaller reproducibility, unnecessary bundled
    files, exe size regression

**Hygiene:**
14. **TODO/FIXME/HACK audit** — resolve or remove stale markers
15. **Log quality** — actionable error messages for both GUI and CLI users

### Deliverable
A review document in `docs/` named `Code-Review-YYYY-MM.md` containing:

- **Regression check**: compare against previous review — note any deferred
  items that are still relevant, and any previously-fixed issues that
  have regressed
- **Summary table**: each finding with Category, Description, Action
  (Remove/Refactor/Replace/Add), Impact (High/Med/Low), Effort (H/M/L),
  Risk (H/M/L)
- **Detailed findings**: grouped by category, ordered by impact descending
  then effort ascending within each group. Each finding must include:
  - Evidence (file path + line, or command to reproduce)
  - Recommendation (specific action to take)
- **Out of scope**: new feature ideas or large refactors that belong in
  `TODO.md`. Criteria: if it adds new user-facing functionality or would
  take more than ~1 hour, it's out of scope for the review.

### Finding statuses
Each finding gets one of these statuses during triage:
- **Implement** — approved, will be done in this cycle
- **Defer** — valid but low priority; carry forward to next review
- **Reject** — investigated, no action needed (include rationale to
  prevent re-raising in future reviews)
- **Out of scope** — belongs in `TODO.md`, not this review

### Process
1. **Discovery** — produce the review document; do NOT implement changes
2. **Triage** — review findings with the user, assign statuses
3. **Implementation** — implement approved items in focused commits, one
   logical change each; re-run tests and linting after each change
4. **Verification** — run full test suite + lint + build smoke test;
   update the review doc's summary table with final statuses

