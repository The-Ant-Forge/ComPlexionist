# Feasibility Study: Migrating ComPlexionist to Tauri (Rust + Vue 3)

*Date: 2026-03-31*

## Context

ComPlexionist currently uses Python + Flet (Flutter-based GUI framework). This study evaluates migrating to **Tauri** with a **Rust backend** and **Vue 3 frontend**, primarily motivated by wanting a modern web UI (HTML/CSS/JS).

---

## Current Codebase at a Glance

| Layer | Lines | Files | Rewrite target |
|-------|-------|-------|---------------|
| Backend (API clients, gap detection, config, cache) | ~6,700 | 20 | Rust |
| GUI (Flet screens, state, theme) | ~6,300 | 13 | Vue 3 |
| Tests | ~4,100 | 11 | Rust tests |
| **Total** | **~17,100** | **44** | |

Current exe: **55.8 MB** (PyInstaller + bundled Flutter desktop client)

---

## Effort Estimate: Full Rust Rewrite

### Phase 1: Rust Backend (8-12 weeks)

| Component | Effort | Risk | Notes |
|-----------|--------|------|-------|
| **Plex API client** | 3-4 weeks | **HIGH** | No Rust crate exists. Must reverse-engineer `plexapi` HTTP calls. `plex/client.py` uses a narrow slice but plexapi does heavy lifting behind the scenes (XML/JSON parsing, GUID formats, auth flows). |
| TMDB client | 1 week | Low | Straightforward REST via reqwest + serde. |
| TVDB client | 1-1.5 weeks | Low | REST with token auth. |
| Config system | 1 week | Medium | `[plex:N]` indexed sections, env var expansion, search paths. Custom parser likely needed. (788 lines) |
| Cache system | 1-1.5 weeks | Low | Single-file JSON with TTL + fingerprints. (634 lines) |
| Gap detection | 2-3 weeks | Medium | Parallel TMDB lookups with rate limiting. ThreadPoolExecutor becomes tokio tasks + semaphore. |
| Stats, ETA, validation, errors | 1 week | Low | Mechanical translation |

### Phase 2: Tauri Shell + IPC (3-4 weeks)

- `#[tauri::command]` handlers for all backend operations
- Event system for scan progress (`AppHandle::emit` replaces Flet's `page.pubsub`)
- Managed state (Rust `AppState` + Pinia stores on Vue side)
- Cancellation via shared `AtomicBool`

### Phase 3: Vue 3 Frontend (6-8 weeks)

| Screen | Current lines | Effort | Notes |
|--------|--------------|--------|-------|
| Results | 1,411 | 2-3 weeks | Largest screen. Filtering, search, collection cards, export. |
| Settings | 998 | 1-1.5 weeks | Multi-server management, ignore lists, path mapping |
| Onboarding | 707 | 1 week | Step-by-step wizard with API key validation |
| Help | 280 | 0.5 week | Static content |
| Dashboard | 273 | 1 week | Connection status, scan launch |
| Scanning | 200 | 1 week | Progress bars, ETA, cancel |

### Phase 4: CLI Port (2-3 weeks)
- Click becomes clap, Rich becomes indicatif + comfy-table

### Phase 5: Testing + Polish (3-4 weeks)
- Port ~4,100 lines of tests, integration testing, platform testing

### Total: 22-31 weeks (5.5-8 months) solo, full-time

If learning Rust concurrently, add 50-80%.

---

## Risk Assessment

### High Risk: Plex API Client from Scratch

`python-plexapi` is a 15+ year old project with 6,000+ commits. ComPlexionist uses a narrow slice, but even that relies on plexapi handling:
- JSON response parsing (`Accept: application/json` header)
- GUID format variations across Plex versions
- Library section enumeration and item retrieval
- Episode hierarchy (show, season, episode)

The Plex REST endpoints are known (documented in `docs/Plex-Background.md`):
- `GET /library/sections` — list libraries
- `GET /library/sections/{id}/all` — all items
- `GET /library/metadata/{id}/allLeaves` — all episodes

But the response shapes are version-dependent and not formally documented. You'd need to capture real responses and build typed structs from them.

### Medium Risk: Concurrency Model

Current: `ThreadPoolExecutor(max_workers=2)` + `threading.Lock` for 0.25s rate limiting.
Target: `tokio::spawn` + `tokio::sync::Semaphore`.

Conceptually similar but fundamentally different execution model. Getting rate-limiting wrong means either API bans or serialised performance.

### Medium Risk: Config Format Compatibility

Users have existing `complexionist.ini` files. The `[plex:N]` indexed section pattern, env var expansion (`${VAR}`), and comma-separated lists need exact compatibility. Standard Rust INI crates may not handle indexed sections natively.

### Low Risk: Everything else

TMDB/TVDB clients, cache, gap detection models, output formatting — these all have clean Rust equivalents and are mechanical translation work.

---

## What You Gain

| Benefit | Details |
|---------|---------|
| **4-7x smaller binary** | ~8-15 MB vs 55.8 MB (Tauri uses system WebView2, no bundled runtime) |
| **Sub-second startup** | No Python interpreter boot, no Flutter client extraction |
| **Modern UI** | Full HTML/CSS/JS. The Results screen (1,411 lines of Flet widget construction) becomes clean Vue components with CSS Grid, animations, component libraries |
| **Clean shutdown** | No more watchdog timers, `os._exit()`, killing `flet.exe`. Tauri lifecycle is clean. |
| **Better dev experience** | Hot reload, browser devtools, CSS vs restart-the-app for every Flet change |
| **Lower memory** | 30-80 MB vs 150-300 MB (Rust + WebView vs Python + Flutter) |
| **Stable foundation** | Tauri is at v2, mature. Flet is 0.x with frequent breaking API changes |

## What You Lose / Gets Harder

| Tradeoff | Details |
|----------|---------|
| **Plex API exploration** | Python: `print(item.__dict__)`. Rust: must define structs upfront. Slower discovery. |
| **Rapid prototyping** | Rust compiler demands correctness upfront. New features take longer to prototype. |
| **String processing verbosity** | Config env var expansion, path mapping with backslash normalisation — routine in Python, more verbose in Rust. |
| **Cache flexibility** | Current cache stores arbitrary dicts. Rust needs typed deserialisation or `serde_json::Value`. |
| **Development time** | 6-8 months vs 0. The current app works. |

---

## Rust Ecosystem Mapping

| Python | Rust | Maturity |
|--------|------|----------|
| plexapi | **None — build from scratch** | N/A |
| httpx | reqwest | Excellent |
| pydantic | serde + serde_json | Excellent (better for this use case) |
| click | clap | Excellent |
| rich | indicatif + comfy-table + colored | Good (multiple crates) |
| configparser | rust-ini / config | Good (may need custom for `[plex:N]`) |
| threading | tokio | Excellent |
| hashlib | md5 crate | Trivial |
| pathlib | std::path | Built-in |

---

## The Hybrid Alternative: Python Backend + Tauri+Vue Frontend

If the primary goal is a modern web UI, there's a much faster path:

**Keep the Python backend as a Tauri sidecar. Only rewrite the GUI in Vue 3.**

| | Full Rewrite | Hybrid | Status Quo |
|---|---|---|---|
| Effort | 22-31 weeks | **4-6 weeks** | 0 |
| Binary size | 8-15 MB | ~70 MB | 55.8 MB |
| Startup | <1s | 3-5s | 3-5s |
| UI quality | Excellent | **Excellent** | Adequate |
| Plex client risk | High | **None** | None |
| Backend performance | Excellent | Good | Good |

**How it works:**
1. Package existing Python backend as a standalone exe (already done via PyInstaller)
2. Tauri launches it as a sidecar process
3. Add a thin HTTP API layer (~200 lines of FastAPI/Flask) to the Python code
4. Vue 3 frontend calls Tauri commands which proxy to the Python HTTP API
5. Rust backend rewrite can happen incrementally later

This delivers the primary user-facing benefit (modern web UI) at ~20% of the cost, with zero risk on the battle-tested Python backend.

---

## Decision Matrix

| If your priority is... | Recommended path |
|------------------------|-----------------|
| Modern web UI (stated goal) | **Hybrid** — 4-6 weeks, immediate UI benefit |
| Smallest possible binary | Full Rust rewrite — 6-8 months |
| Learning Rust | Full rewrite — great learning project, expect 9-12 months |
| Minimising risk | Hybrid first, then incremental Rust migration |
| Staying productive on features | Status quo (Flet) or Hybrid |

---

## Recommendation

**Start with the hybrid approach.** It delivers the main thing you want (Vue 3 UI with HTML/CSS/JS) in 4-6 weeks. The Python backend stays intact, tested, and working. If you later want the full Rust backend for binary size or performance, you can incrementally replace the Python sidecar — but you'll already have a shipping product with the modern UI.

If the full Rust rewrite is the goal regardless, **start with the Plex API client** — it's the highest-risk item. If you can build a working Plex client in Rust that passes the existing tests, the rest is mechanical.
