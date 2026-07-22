# -*- mode: python ; coding: utf-8 -*-
"""PyInstaller spec for Twelve-Tone Music Analyzer — macOS."""

from PyInstaller.utils.hooks import collect_all


datas = []
binaries = []
hiddenimports = [
    # PyQt5
    'PyQt5',
    'PyQt5.QtCore',
    'PyQt5.QtGui',
    'PyQt5.QtWidgets',
    'PyQt5.sip',
    # music21
    'music21.serial',
    'music21.converter.subConverters',
    'music21.mei',
    'music21.mei.base',
    'music21.mei.translate',
    'music21.midi',
    'music21.midi.translate',
    'music21.musicxml',
    'music21.musicxml.xmlToM21',
    'music21.musicxml.m21ToXml',
    'music21.graph',
    'music21.graph.plot',
    'music21.graph.utilities',
    'music21.lily',
    'music21.lily.translate',
    'music21.analysis',
    'music21.analysis.discrete',
    # matplotlib
    'matplotlib',
    'matplotlib.backends.backend_qt5agg',
    'matplotlib.pyplot',
    # numpy / scipy
    'numpy',
    'numpy.core._methods',
    'scipy',
    'scipy.interpolate',
    'scipy.signal',
    # librosa
    'librosa',
    'librosa.display',
    # sklearn
    'sklearn',
    'sklearn.preprocessing',
    # networkx
    'networkx',
    # project
    'src',
    'src.core',
    'src.core.file_manager',
    'src.core.score_analyzer',
    'src.core.twelve_tone',
    'src.core.chord_analyzer',
    'src.core.audio_analyzer',
    'src.core.inclusion_lattice',
    'src.core.set_relations',
    'src.ui',
    'src.ui.main_window',
    'src.ui.theme',
    'src.ui.tabs',
    'src.ui.tabs.overview_tab',
    'src.ui.tabs.visualization_tab',
    'src.ui.tabs.twelve_tone_tab',
    'src.ui.tabs.chord_tab',
    'src.ui.tabs.audio_tab',
    'src.ui.tabs.lattice_tab',
    'src.ui.tabs.annotated_score_tab',
    'src.ui.tabs.forte_name_tab',
    'src.ui.tabs.set_relations_tab',
    'src.ui.widgets',
    'src.ui.widgets.plot_canvas',
    'src.ui.widgets.matrix_widget',
    'src.ui.widgets.score_view',
    'src.ui.widgets.score_opener',
    'src.ui.widgets.collapsible_panel',
    'src.ui.dialogs.update_dialog',
    'src.core.updater',
    'src.ui.dialogs',
    'src.ui.dialogs.settings_dialog',
    'src.ui.dialogs.musescore_prompt',
    'src.utils',
    'src.utils.config',
    'src.utils.i18n',
]

# Collect all from PyQt5, music21, and scipy (C extensions often missed)
for _pkg in ('PyQt5', 'music21', 'scipy'):
    _ret = collect_all(_pkg)
    datas += _ret[0]
    binaries += _ret[1]
    hiddenimports += _ret[2]


a = Analysis(
    ['main.py'],
    pathex=['.'],
    binaries=binaries,
    datas=datas + [('resources/', 'resources'), ('assets/', 'assets')],
    hiddenimports=hiddenimports,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=['pyi_rth_music21.py'],
    excludes=[],
    noarchive=False,
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=None,
)

pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.datas,
    exclude_binaries=True,
    name='TwelveToneAnalyzer',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=False,                  # UPX can break macOS signing
    console=False,              # GUI app — no terminal window
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon='app_icon.icns',       # macOS icon file
)

app = BUNDLE(
    exe,
    name='TwelveToneAnalyzer.app',
    icon='app_icon.icns',
    bundle_identifier='com.musicanalysis.twelvetoneanalyzer',
    info_plist={
        'NSPrincipalClass': 'NSApplication',
        'NSHighResolutionCapable': 'True',
        'CFBundleName': 'Twelve-Tone Music Analyzer',
        'CFBundleShortVersionString': '1.4.4',
        'CFBundleVersion': '1.4.4',
        'CFBundleInfoDictionaryVersion': '6.0',
        'CFBundlePackageType': 'APPL',
        'LSMinimumSystemVersion': '10.15',
        'NSHumanReadableCopyright': '© 2025 Yvonne',
    },
)
