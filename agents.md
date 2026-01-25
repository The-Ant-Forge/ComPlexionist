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
- `Docs/Plex-Background.md` — Plex API research and technical background
- `Docs/Specification.md` — detailed feature specs and architecture
- `Docs/TODO.md` — forward-looking work items
- `Docs/Completed.md` — durable record of finished work
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
.venv/Scripts/python.exe -m pytest tests/ -v

# Run linting
.venv/Scripts/python.exe -m ruff check src tests

# Auto-fix lint issues
.venv/Scripts/python.exe -m ruff check --fix src tests

# Run the CLI
.venv/Scripts/complexionist.exe --help
.venv/Scripts/complexionist.exe movies --help
.venv/Scripts/complexionist.exe episodes --help
.venv/Scripts/complexionist.exe config show
.venv/Scripts/complexionist.exe cache stats
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

## TODO + Completed workflow (docs-driven)

This repo keeps:
- **future work** in `Docs/TODO.md`, and
- a durable **completed-work record** in `Docs/Completed.md`.

This avoids `Docs/TODO.md` turning into a changelog while still preserving engineering context (what shipped, why it mattered, and where it lives).

When implementing an item from `Docs/TODO.md`:
1. **Do the implementation first**, including tests.
2. **Update `Docs/TODO.md` (future only)**:
   - Move completed items out.
   - Add/adjust any new items discovered during the work.
   - Keep the file focused on *forward-looking* items.
3. **Add a record to `Docs/Completed.md`**:
   - Title, Why, Where (key files/classes), What we did.
   - Capture important assumptions/gotchas.
4. **Clean up in-code TODO comments**:
   - Remove TODOs that are now addressed.
5. **Prefer small commits**:
   - Ideally: one commit per focused TODO item.

Goal: keep code clean, keep `Docs/TODO.md` as the single source of truth for future work, and keep `Docs/Completed.md` as the durable record of finished work.

---

## Git workflow (commit and push)

Common sequence:
```
git status
git diff
git add <specific-files>
git commit -m "Meaningful summary of change"
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

1. Builds Windows executable with PyInstaller
2. Tests the executable (`--version`, `--help`)
3. Creates GitHub Release with:
   - Release name: "ComPlexionist vX.Y.Z"
   - Release body: Contents of `RELEASE_NOTES.md`
   - Attached asset: `complexionist.exe`

---

## Local Exe Build

Build a Windows executable locally for testing before creating a release.

### Prerequisites
PyInstaller is included in dev dependencies. If not installed:
```bash
.venv/Scripts/pip.exe install pyinstaller
```

### Build command
```bash
.venv/Scripts/python.exe -m PyInstaller --onefile --name complexionist --console src/complexionist/cli.py --distpath dist --workpath build --specpath .
```

### Output
- Executable: `dist/complexionist.exe`
- Build artifacts: `build/` (gitignored)
- Spec file: `complexionist.spec` (gitignored)

### Verify the build
```bash
dist/complexionist.exe --version
dist/complexionist.exe --help
```

### When to build locally
Build an exe for testing after making code changes to:
- `src/complexionist/**/*.py` - Any Python source files
- `pyproject.toml` - Dependencies or entry points

No need to rebuild for:
- `Docs/**` - Documentation only
- `tests/**` - Test files only
- `README.md`, `agents.md` - Markdown files
- `.github/**` - CI/CD configuration

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
3. Add/modify feature descriptions
4. Commit the changes
5. Then create the tag

---

## Repository hygiene / gotchas

- **Line endings:** Windows checkouts may flip LF/CRLF depending on Git settings. Avoid churn by not reformatting unrelated files.
- **Secrets:** Never commit API keys or tokens. Use a `complexionist.ini` file (gitignored).
- **Generated outputs:** `build/`, `dist/`, `__pycache__/`, `.venv/` should not be committed.
- **`Docs/`** is tracked and intended for specs/planning.

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
