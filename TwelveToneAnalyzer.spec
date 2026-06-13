# -*- mode: python ; coding: utf-8 -*-


a = Analysis(
    ['main.py'],
    pathex=[],
    binaries=[],
    datas=[('resources', 'resources'), ('.venv_mac/lib/python3.9/site-packages/music21/corpus', 'music21/corpus')],
    hiddenimports=['PyQt5', 'music21', 'matplotlib', 'numpy', 'scipy', 'librosa', 'sklearn', 'networkx', 'src', 'src.core', 'src.ui', 'src.utils', 'matplotlib.backends.backend_qt5agg'],
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
    [],
    exclude_binaries=True,
    name='TwelveToneAnalyzer',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon=['app_icon.icns'],
)
coll = COLLECT(
    exe,
    a.binaries,
    a.datas,
    strip=False,
    upx=True,
    upx_exclude=[],
    name='TwelveToneAnalyzer',
)
app = BUNDLE(
    coll,
    name='TwelveToneAnalyzer.app',
    icon='app_icon.icns',
    bundle_identifier=None,
)
