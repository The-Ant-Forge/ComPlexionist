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

### Package Structure
```
src/complexionist/gui/
├── __init__.py        # Package exports (run_app)
├── app.py             # Main app, navigation, scan execution
├── state.py           # AppState dataclass (all UI state)
├── theme.py           # Plex gold theme, colors (imports from constants.py)
├── strings.py         # UI strings (i18n ready)
├── errors.py          # GUI error display helpers (imports from errors.py)
├── window_state.py    # Window size/position persistence
└── screens/
    ├── __init__.py    # Screen exports
    ├── base.py        # BaseScreen abstract class
    ├── dashboard.py   # Home screen with scan buttons
    ├── onboarding.py  # First-run setup wizard
    ├── results.py     # Results with search/export/ignore
    ├── scanning.py    # Progress display with live stats
    └── settings.py    # Settings panel with ignore list management
```

### Shared Modules
The GUI uses shared modules from the package root:
- `constants.py` - PLEX_GOLD color, score thresholds
- `errors.py` - get_friendly_message() for error translation
- `validation.py` - test_connections() for connection testing

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
[plex]
url = http://your-plex-server:32400
token = your-plex-token

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

### Compile/test locally after changes
Preferred loop:
1. Make a small, targeted change.
2. Run tests/linting after each change.
3. Only then commit/push.

---

## Pre-commit checks (REQUIRED)

Before committing changes, always run these checks to catch CI failures early:

```bash
# Run Ruff linter (catches import errors, unused vars, etc.)
uv run ruff check src tests

# Run Ruff formatter check (catches formatting issues)
uv run ruff format --check src tests

# Auto-fix ruff issues (if any)
uv run ruff check --fix src tests
uv run ruff format src tests
```

### MyPy (optional but recommended)
MyPy type checking is informational in CI (`continue-on-error: true`), but running it locally helps catch type errors in new code:

```bash
# Run type checking
uv run mypy src/complexionist --ignore-missing-imports
```

**Note:** Pre-existing mypy errors exist in the codebase (Flet types, external libs). Focus on ensuring your new code doesn't introduce additional errors.

### Quick pre-commit checklist
```bash
# Minimum checks before every commit:
uv run ruff check src tests && uv run ruff format --check src tests

# If checks fail, auto-fix then re-check:
uv run ruff check --fix src tests && uv run ruff format src tests
```

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

## GitHub CLI (`gh`) usage

The GitHub CLI is useful for:
- watching Actions runs / build status
- viewing logs
- downloading artifacts
- creating PRs
- creating Releases

Assumptions:
- the local repo is connected to the correct GitHub remote
- you are authenticated (`gh auth status`)

Common commands:

List recent runs for `main`:
```
gh run list --branch main --limit 10
```

Watch the latest run until completion:
```
gh run watch --exit-status
```

View logs (useful on failures):
```
gh run view --log-failed
```

Download artifacts from the latest run:
```
gh run download --dir ./artifacts
```

---

## CI/CD Workflows

This project uses GitHub Actions for continuous integration and automated releases.

### Workflows

| Workflow | File | Trigger | Purpose |
|----------|------|---------|---------|
| Python | `.github/workflows/ci.yml` | Push/PR to main | Run tests, linting, type checking |
| Windows | `.github/workflows/build.yml` | Push tag `v*` | Build Windows exe, create release |

### Python Workflow (`ci.yml`)

Runs on every push and PR to `main`:

1. **Test job** (matrix: Python 3.11, 3.12)
   - Checkout with full history (for version calculation)
   - Install dependencies (`pip install -e ".[dev]"`)
   - Run Ruff linter (`ruff check src tests`)
   - Run Ruff formatter check (`ruff format --check src tests`)
   - Run pytest (`pytest -v`)

2. **Type Check job** (informational, `continue-on-error: true`)
   - Run MyPy (`mypy src/complexionist`)
   - Pre-existing type errors exist; this job is informational only

Check CI status:
```bash
gh run list --branch main --limit 5
gh run view --log-failed  # on failures
```

### Build Workflow (`build.yml`)

Triggered by pushing a version tag (`v*`). Automatically:

1. Builds Windows executable from committed `complexionist.spec` via PyInstaller
2. Tests the executable (`--version`, `--cli --help`)
3. Creates GitHub Release with:
   - Release name: "ComPlexionist vX.Y.Z"
   - Release body: Contents of `RELEASE_NOTES.md`
   - Attached asset: `complexionist.exe`

---

## Local Exe Build

Build a Windows executable locally for testing before creating a release.

### Prerequisites
Flet CLI is included as a dependency. PyInstaller is included in dev dependencies.

### Build command

The project has a committed `complexionist.spec` file that handles everything: dynamic package path resolution, all excludes, flet_desktop bundling, and icon embedding.

```bash
# IMPORTANT: pyinstaller clears the dist/ folder, which deletes your test config/cache!
# Use this backup/restore workflow to preserve them.

# Step 1: Backup config and cache (if they exist)
mkdir -p /tmp/complexionist-backup
cp dist/complexionist.ini /tmp/complexionist-backup/ 2>/dev/null || true
cp dist/complexionist.cache.json /tmp/complexionist-backup/ 2>/dev/null || true

# Step 2: Build from committed spec file
uv run pyinstaller complexionist.spec --noconfirm

# Step 3: Restore config and cache
cp /tmp/complexionist-backup/complexionist.ini dist/ 2>/dev/null || true
cp /tmp/complexionist-backup/complexionist.cache.json dist/ 2>/dev/null || true
```

**PowerShell version:**
```powershell
# Backup
New-Item -ItemType Directory -Force -Path $env:TEMP\complexionist-backup | Out-Null
Copy-Item dist\complexionist.ini $env:TEMP\complexionist-backup\ -ErrorAction SilentlyContinue
Copy-Item dist\complexionist.cache.json $env:TEMP\complexionist-backup\ -ErrorAction SilentlyContinue

# Build from committed spec file
uv run pyinstaller complexionist.spec --noconfirm

# Restore
Copy-Item $env:TEMP\complexionist-backup\complexionist.ini dist\ -ErrorAction SilentlyContinue
Copy-Item $env:TEMP\complexionist-backup\complexionist.cache.json dist\ -ErrorAction SilentlyContinue
```

**Why this matters:** The exe looks for config in its own directory first. Keeping `complexionist.ini` and `complexionist.cache.json` in dist/ creates a self-contained test environment. Without them, you'll need to re-run the setup wizard and rebuild the API cache (which can take minutes with a large library).

### Spec file (`complexionist.spec`)

The spec file dynamically finds package directories using `importlib`, so it works across venvs and system installs. Key features:

- **Dynamic package paths** - `_pkg_dir()` helper finds flet and flet_desktop at build time
- **Flet desktop runtime** - Bundles `flet_desktop/app` (Flutter executable + all plugins)
- **All excludes configured** - Dev tools, unused heavy packages (numpy, pandas, matplotlib)
- **Icon and console settings** - `icon.ico` embedded, console disabled for GUI mode

### Size optimization

The spec file excludes packages not needed at runtime, reducing the exe from ~92MB to ~55MB:

| Excluded Package | Why |
|-----------------|-----|
| mypy | Type checker, dev-only |
| pip | Package installer, not needed at runtime |
| setuptools, wheel, pkg_resources | Build tools, not needed at runtime |
| tzdata | Timezone data, not used |
| pygments | Syntax highlighting, not needed in GUI app |
| numpy, pandas, matplotlib, scipy | Transitive deps from plexapi, not used by our code |
| PIL, tkinter | Image/GUI libs not used |
| pytest, py, _pytest | Test framework, dev-only |

**Cannot exclude (required by Flet):**
- All flet_desktop DLLs (Flutter loads all compiled-in plugins at startup)

### What gets preserved in dist/
When testing locally, the dist folder may contain:
- `complexionist.exe` - The built executable (replaced on each build)
- `complexionist.ini` - Your test configuration (preserve this!)
- `complexionist.cache.json` - Cached API responses (preserve this!)

The exe looks for config in its own directory first, making dist/ a self-contained test environment.

### Output
- Executable: `dist/complexionist.exe` (~55 MB with optimizations)
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

### Pre-release checklist

1. **Verify CI is passing:**
   ```bash
   gh run list --branch main --limit 1
   ```

2. **Check current version:**
   ```bash
   git rev-list --count HEAD
   # Result: 15 → version will be 1.1.15
   ```

3. **Ensure RELEASE_NOTES.md is up to date:**
   - Update version number in the header
   - Document new features, changes, requirements
   - Commit any updates before tagging

4. **Review and update Help content:**
   - Check `src/complexionist/gui/screens/help.py` for the embedded user guide
   - Add documentation for any new features
   - Update descriptions for changed features
   - Remove references to removed features
   - Commit any updates before tagging

### Create release

```bash
# Create annotated tag (recommended for releases)
git tag -a v1.1.15 -m "Release v1.1.15"

# Push the tag to trigger build workflow
git push origin v1.1.15
```

### Monitor the build

```bash
# Watch the build workflow
gh run watch --exit-status

# Or list recent workflow runs
gh run list --workflow=build.yml --limit 5

# View build logs if something fails
gh run view --log-failed
```

### Verify release

```bash
# List releases
gh release list

# View specific release
gh release view v1.1.15

# Download the executable
gh release download v1.1.15 --dir ./release-artifacts
```

### Manual release editing (if needed)

```bash
# Edit release notes after creation
gh release edit v1.1.15 --notes-file RELEASE_NOTES.md

# Add additional files to an existing release
gh release upload v1.1.15 ./additional-file.zip
```

---

## Release Notes (`RELEASE_NOTES.md`)

The `RELEASE_NOTES.md` file at the repo root is used as the GitHub Release body.

### Structure

```markdown
# ComPlexionist vX.Y.Z - Release Title

**Release Date:** Month Year
**Version:** X.Y.Z

## Overview
Brief description of what this release contains.

## Key Features
- Feature 1
- Feature 2

## Requirements
- System requirements
- API keys needed

## Available Builds
- Windows executable details
- Python package details

## Quick Start
Installation and basic usage.

## Command Reference
Available commands and options.
```

### Updating for a new release

1. Update the version number in the header
2. Update the release date
3. Add/modify feature descriptions (New Features → Code Improvements → Bug Fixes)
4. Commit the changes
5. Then create the tag

### GitHub Release Page

When creating the GitHub release, the release title duplicates the RELEASE_NOTES.md headline. To avoid redundancy:

1. Copy the RELEASE_NOTES.md content for the release body
2. **Remove the first headline** (e.g., `# ComPlexionist v2.0.86 - Collection Folder Organization`)
3. Start the release body from the **Release Date** line or **Overview** section

This keeps the release page clean since GitHub already shows the release title.

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
