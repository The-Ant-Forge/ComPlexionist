# -*- mode: python ; coding: utf-8 -*-
import importlib, os
from pathlib import Path

def _pkg_dir(name):
    """Find a package's directory regardless of venv or system install."""
    try:
        return os.path.dirname(importlib.import_module(name).__file__)
    except ModuleNotFoundError:
        raise ModuleNotFoundError(
            f"Package '{name}' not found. Install it with: pip install {name.replace('_', '-')}"
        )

_flet_dir = _pkg_dir('flet')

# Flet 0.83+ downloads the desktop client on first run and caches it at
# ~/.flet/client/flet-desktop-{flavor}-{version}/. For PyInstaller, we bundle
# this as flet-windows.zip in flet_desktop/app/ so ensure_client_cached() finds
# the bundled archive and extracts it to the user's cache (no download needed).
_flet_client_cache = Path.home() / '.flet' / 'client'
_flet_client_dirs = sorted(_flet_client_cache.glob('flet-desktop-full-*'))
if not _flet_client_dirs:
    _flet_client_dirs = sorted(_flet_client_cache.glob('flet-desktop-*'))
if not _flet_client_dirs:
    raise FileNotFoundError(
        "Flet desktop client not cached. Run the app once with 'uv run complexionist' "
        "to download the client, then retry the build."
    )
_flet_client_dir = _flet_client_dirs[-1]

# Create flet-windows.zip from cached client for bundling
import zipfile, tempfile
_flet_zip = os.path.join(tempfile.gettempdir(), 'flet-windows.zip')
with zipfile.ZipFile(_flet_zip, 'w', zipfile.ZIP_DEFLATED) as zf:
    for root, dirs, files in os.walk(_flet_client_dir):
        for f in files:
            full = os.path.join(root, f)
            zf.write(full, os.path.relpath(full, _flet_client_dir))

a = Analysis(
    ['src\\complexionist\\cli.py'],
    pathex=[],
    binaries=[],
    datas=[
        (os.path.join(_flet_dir, 'controls'), 'flet/controls'),
        (_flet_zip, 'flet_desktop/app'),
        ('assets', 'assets'),
    ],
    hiddenimports=[],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[
        # 'pygments' exclude is safe because no rich module the app imports pulls
        # pygments; using rich.traceback/rich.markdown/rich.syntax would work in
        # dev but break the frozen exe — re-verify this exclude if those are ever used.
        'mypy', 'pip', 'setuptools', 'wheel', 'pkg_resources', 'tzdata', 'pygments',
        'numpy', 'pandas', 'matplotlib', 'scipy', 'PIL', 'tkinter',
        'pytest', 'py', '_pytest',
    ],
    noarchive=False,
    optimize=0,
)
pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.datas,
    [],
    name='complexionist',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=False,  # UPX not installed everywhere; keeps builds reproducible and avoids AV false positives
    upx_exclude=[],
    runtime_tmpdir=None,
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    version=None,
    icon=['icon.ico'],
)
