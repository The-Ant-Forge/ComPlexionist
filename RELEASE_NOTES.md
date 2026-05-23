# ComPlexionist v2.0.145 - Supply-Chain Security & Hardening

**Release Date:** May 2026
**Version:** 2.0.145

---

## Overview

This is a security-driven maintenance release. It resolves three open Dependabot advisories (two high, one moderate) by upgrading `urllib3` and `idna` to their patched versions, and introduces automated Dependabot configuration so future supply-chain risks are flagged — and patched — on a known cadence rather than discovered by chance.

No user-facing features, settings, or workflows have changed. Existing configurations and caches remain compatible.

---

## Security Fixes

### urllib3 — High-severity advisories (GHSA-mf9v-mfxr-j63j, GHSA-qccp-gfcp-xxvc)
- **Decompression-bomb safeguards bypass** in parts of the streaming API
- **Sensitive headers forwarded across origins** on proxied low-level redirects
- Mitigated by upgrading the transitive `urllib3` dependency from 2.6.3 to **2.7.0**
- Reaches ComPlexionist via the `requests` / `plexapi` / `httpx` HTTP stack

### idna — Moderate-severity advisory (GHSA-65pc-fj4g-8rjx)
- Crafted inputs to `idna.encode()` could bypass the CVE-2024-3651 fix
- Mitigated by upgrading from 3.11 to **3.15**
- Relevant anywhere hostnames are resolved (Plex / TMDB / TVDB URLs)

The `requests` floor in `pyproject.toml` was raised to `>=2.34.0` to keep the explicit CVE pin aligned with the installed version, so fresh installs that read the manifest (not the lockfile) cannot silently roll back to a vulnerable transitive resolution.

---

## Improvements

### Automated Dependency Management
A new `.github/dependabot.yml` configures weekly version-update PRs for both Python (`pip` / `uv.lock`) and GitHub Actions workflows.

- **Cooldown:** 7-day default — aligns with the local `uv` minimum-release-age quarantine so PRs don't propose versions the dev machine refuses to install
- **Grouping:** Minor and patch updates are grouped into a single PR to reduce noise; major bumps stay individual so they can be reviewed deliberately
- **Security advisories:** Continue to fire immediately and are not subject to cooldown — this is the intended behavior

### Dependencies
- urllib3 2.6.3 → **2.7.0** (security)
- idna 3.11 → **3.15** (security)
- requests 2.33.1 → **2.34.2** (CVE pin raised to `>=2.34.0`)
- click 8.3.2 → 8.3.3
- ruff 0.15.10 → 0.15.13
- pyinstaller 6.19.0 → 6.20.0
- pyinstaller-hooks-contrib 2026.4 → 2026.5
- certifi 2026.2.25 → 2026.4.22
- markdown-it-py 4.0.0 → 4.2.0
- packaging 26.0 → 26.2
- pathspec 1.0.4 → 1.1.1
- types-pyyaml, types-requests (stub refreshes)

---

## Bug Fixes

None in this release.

---

## Upgrade Notes

- No configuration changes needed
- Cache files from previous versions remain compatible
- After installing, Dependabot will perform an initial scan and may open PRs for further deferred updates (e.g. `flet`, `pydantic`, `mypy`, `rich`) — these were intentionally not bundled into this release because they carry higher regression risk and warrant individual evaluation

---

## Support & Contributing

- **Issues:** [GitHub Issues](https://github.com/The-Ant-Forge/ComPlexionist/issues)
- **Repository:** [GitHub](https://github.com/The-Ant-Forge/ComPlexionist)

---

## License

MIT License - See [LICENSE](LICENSE) for details.
