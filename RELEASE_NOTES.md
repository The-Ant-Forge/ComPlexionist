# ComPlexionist v2.0.128 - Dependency Updates & Performance

**Release Date:** March 2026
**Version:** 2.0.126

---

## Overview

This release upgrades Flet to 0.83.0, bringing a faster UI rendering engine with sparse prop tracking. Users should notice improved responsiveness, especially during scans with many controls updating. All other dependencies have been updated to their latest stable versions.

---

## Improvements

### Performance
- **Flet 0.83 sparse prop tracking** — UI updates now diff only changed properties instead of the entire control tree. This means faster `page.update()` calls across the board — particularly noticeable during scans and on the results screen with hundreds of collection/show cards.
- **Reduced redundant updates** — Event handlers that explicitly call `.update()` no longer trigger an additional auto-update, eliminating double-renders.

### Dependencies
- flet 0.82.2 → 0.83.0 (sparse prop tracking, new client distribution model)
- plexapi 4.17.x → 4.18.1 (pin updated to >=4.18.0)
- ruff 0.15.6 → 0.15.8
- rich 14.3.2 → 14.3.3
- python-dotenv 1.2.1 → 1.2.2
- pyinstaller-hooks-contrib updated

### Build System
- Updated PyInstaller spec for Flet 0.83's new desktop client distribution model
- Desktop client binary is now bundled as a zip archive, extracted to user cache on first run
- Exe remains fully self-contained (no internet download needed)

---

## Bug Fixes

- None in this release

---

## Upgrade Notes

- No configuration changes needed
- The first launch after upgrading extracts the bundled Flet desktop client to `~/.flet/client/` — this is automatic and takes a moment

---

## Support & Contributing

- **Issues:** [GitHub Issues](https://github.com/The-Ant-Forge/ComPlexionist/issues)
- **Repository:** [GitHub](https://github.com/The-Ant-Forge/ComPlexionist)

---

## License

MIT License - See [LICENSE](LICENSE) for details.
