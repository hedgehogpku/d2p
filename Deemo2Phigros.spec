# -*- mode: python ; coding: utf-8 -*-


a = Analysis(
    ['desktop_ui.py'],
    pathex=[],
    binaries=[],
    datas=[('themes', 'themes'), ('default_cover.png', '.'), ('LXGWWenKai-Regular.ttf', '.')],
    hiddenimports=['mutagen', 'dnt_reader', 'dnt_extractor', 'convert_core_function'],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
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
    name='Deemo2Phigros',
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
    icon=['piano.ico'],
)
