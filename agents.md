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
```

### Environment variables (.env file)
```bash
PLEX_URL=http://your-plex-server:32400
PLEX_TOKEN=your-plex-token
TMDB_API_KEY=your-tmdb-api-key
TVDB_API_KEY=your-tvdb-api-key
```

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

## Manual GitHub Release procedure

This project intentionally does **not** auto-release on every successful build. Releases are created manually when you decide the current state is ready.

### Release notes format (Markdown)
When creating/editing a GitHub Release, write release notes in **Markdown** and use this structure:

1. **New features / improvements** (first)
2. **Bug fixes** (second)
3. Optional: Requirements / Artifacts / CI run link

### Keep a committed release-notes record (recommended)
Write the release notes into a versioned Markdown file under `Docs/`, then publish that file as the GitHub Release body.

Suggested filename:
- `Docs/release-notes-vX.Y.Z.md`

Workflow:
1. Create/update the notes file and commit it.
2. Publish it to the GitHub Release body:
```
gh release edit vX.Y.Z --notes-file Docs/release-notes-vX.Y.Z.md
```

### Versioning
- Use semantic versioning: `vMAJOR.MINOR.PATCH`
- Tag releases accordingly

### Steps (high level)
1. Confirm `HEAD` is the commit you want to release.
2. Confirm there is a successful CI run for that commit.
3. Confirm the tag does **not** already exist.
4. Create and push the git tag:
```
git tag vX.Y.Z
git push origin vX.Y.Z
```
5. Create the GitHub Release and upload assets.

---

## Repository hygiene / gotchas

- **Line endings:** Windows checkouts may flip LF/CRLF depending on Git settings. Avoid churn by not reformatting unrelated files.
- **Secrets:** Never commit API keys or tokens. Use environment variables or a `.env` file (gitignored).
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
