# -*- mode: python ; coding: utf-8 -*-
from PyInstaller.utils.hooks import collect_dynamic_libs
from PyInstaller.utils.hooks import collect_all

datas = []
binaries = []
hiddenimports = ['matplotlib.backends.backend_qt5agg', 'PyQt5.sip', 'matplotlib.pyplot', 'music21.mei', 'music21.mei.base', 'music21.mei.translate', 'music21.midi', 'music21.midi.translate', 'music21.musicxml', 'music21.musicxml.xmlToM21', 'music21.musicxml.m21ToXml', 'music21.converter.subConverters', 'music21.graph', 'music21.graph.plot', 'music21.graph.utilities', 'music21.lily', 'music21.lily.translate', 'music21.analysis', 'music21.analysis.discrete', 'librosa', 'scipy.interpolate', 'scipy.signal', 'numpy']
binaries += collect_dynamic_libs('PyQt5')
tmp_ret = collect_all('PyQt5')
datas += tmp_ret[0]; binaries += tmp_ret[1]; hiddenimports += tmp_ret[2]
tmp_ret = collect_all('music21')
datas += tmp_ret[0]; binaries += tmp_ret[1]; hiddenimports += tmp_ret[2]


a = Analysis(
    ['main.py'],
    pathex=[],
    binaries=binaries,
    datas=datas,
    hiddenimports=hiddenimports,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=['pyi_rth_qt_dll.py'],
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
    name='TwelveToneAnalyzer_debug',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    console=True,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
)
coll = COLLECT(
    exe,
    a.binaries,
    a.datas,
    strip=False,
    upx=True,
    upx_exclude=[],
    name='TwelveToneAnalyzer_debug',
)
