# -*- mode: python ; coding: utf-8 -*-


a = Analysis(
    ['src\\complexionist\\cli.py'],
    pathex=[],
    binaries=[],
    datas=[('.venv/Lib/site-packages/flet/controls', 'flet/controls'), ('assets', 'assets')],
    hiddenimports=[],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=['mypy', 'pip', 'setuptools', 'wheel', 'pkg_resources', 'tzdata'],
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
    version='C:\\Users\\Steph\\AppData\\Local\\Temp\\75182fcb-eae2-498b-853c-deaaad94df89',
    icon=['icon.ico'],
)
