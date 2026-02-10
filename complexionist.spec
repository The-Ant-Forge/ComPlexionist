# -*- mode: python ; coding: utf-8 -*-
import importlib, os

def _pkg_dir(name):
    """Find a package's directory regardless of venv or system install."""
    return os.path.dirname(importlib.import_module(name).__file__)

_flet_dir = _pkg_dir('flet')
_flet_desktop_dir = _pkg_dir('flet_desktop')

a = Analysis(
    ['src\\complexionist\\cli.py'],
    pathex=[],
    binaries=[],
    datas=[
        (os.path.join(_flet_dir, 'controls'), 'flet/controls'),
        (os.path.join(_flet_desktop_dir, 'app'), 'flet_desktop/app'),
        ('assets', 'assets'),
    ],
    hiddenimports=[],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[
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
    upx=True,
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
