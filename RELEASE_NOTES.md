# ComPlexionist v2.0.148 - GUI Crash Fix & Security Hotfix

**Release Date:** May 2026
**Version:** 2.0.148

---

## Overview

This is a hotfix release. It addresses two issues that affected v2.0.145:

1. **A GUI crash on launch** caused by calls to deprecated Flet module-level functions that PyInstaller could not reliably bundle.
2. **Security-patch rollback** in v2.0.145's lockfile. The v2.0.145 release notes credited `urllib3 2.7.0` and `idna 3.15` as fixing three Dependabot advisories — but a local `uv` re-resolution under the 7-day release-age quarantine silently rolled the lockfile back to vulnerable versions before the exe was built. The published v2.0.145 exe shipped with `urllib3 2.6.3` and `idna 3.11`, *not* the patched versions. This release correctly bundles the patched versions and uses per-package cooldown overrides in the lockfile workflow to prevent recurrence.

If you installed v2.0.145, please upgrade to v2.0.148.

---

## Bug Fixes

### GUI crash from deprecated Flet API calls
- The bundled exe crashed on launch with errors like `module 'flet.controls.padding' has no attribute 'symmetric'` and `module 'flet.controls.border' has no attribute 'all'`
- Root cause: code used Flet's deprecated module-level wrappers (`ft.padding.symmetric`, `ft.border.all`, `ft.margin.only`, `ft.border_radius.all`). These remain present in Flet 0.84.0 but are wrapped by a `@deprecated` decorator that PyInstaller's static analysis cannot reliably trace into the bundle
- Fix: all 28 callsites migrated to the non-deprecated classmethod form (`ft.Padding.symmetric`, `ft.Border.all`, `ft.Margin.only`, `ft.BorderRadius.all`)
- Dev mode masked the bug because the deprecated wrappers exist at runtime; only the PyInstaller-bundled exe surfaced it

---

## Security Fixes (actually bundled this time)

The following advisories were credited as resolved in v2.0.145 but did not make it into that artifact due to the lockfile rollback described above. They are correctly bundled in v2.0.148:

### urllib3 — High-severity (GHSA-mf9v-mfxr-j63j, GHSA-qccp-gfcp-xxvc)
- Decompression-bomb safeguards bypass in parts of the streaming API
- Sensitive headers forwarded across origins on proxied low-level redirects
- Mitigated by upgrading the transitive `urllib3` dependency to **2.7.0**

### idna — Moderate-severity (GHSA-65pc-fj4g-8rjx)
- Crafted inputs to `idna.encode()` could bypass the CVE-2024-3651 fix
- Mitigated by upgrading to **3.15**

`pyproject.toml` now carries explicit CVE pins (`urllib3>=2.7.0`, `idna>=3.15`) alongside the existing `requests`/`pygments` pins, so any future re-resolution that satisfies the manifest cannot silently roll these packages back to vulnerable versions.

---

## Improvements

### Dependencies
- **urllib3 2.6.3 → 2.7.0** (security)
- **idna 3.11 → 3.15** (security)
- certifi 2026.2.25 → 2026.4.22
- click 8.3.2 → 8.4.0
- markdown-it-py 4.0.0 → 4.2.0

---

## Upgrade Notes

- **If you are running v2.0.145, please upgrade.** That release's exe both crashes on GUI launch and lacks the security patches its notes credited
- No configuration changes are required
- Cache files from previous versions remain compatible

---

## Support & Contributing

- **Issues:** [GitHub Issues](https://github.com/The-Ant-Forge/ComPlexionist/issues)
- **Repository:** [GitHub](https://github.com/The-Ant-Forge/ComPlexionist)

---

## License

MIT License - See [LICENSE](LICENSE) for details.
