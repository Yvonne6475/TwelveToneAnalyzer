# -*- mode: python ; coding: utf-8 -*-
"""PyInstaller spec for TMA Auto-Updating Launcher — macOS.

This produces a tiny (~25 MB) .app that:
1. Shows a progress dialog while git-cloning/pulling the full repo
2. Creates a managed venv with all dependencies
3. Launches main.py from the cloned repo

The heavy dependencies (music21, numpy, scipy, librosa) live in the
git-managed venv, not in the .app bundle.  Every restart = auto-update.
"""

from PyInstaller.utils.hooks import collect_all

datas = []
binaries = []
hiddenimports = [
    'PyQt5',
    'PyQt5.QtCore',
    'PyQt5.QtGui',
    'PyQt5.QtWidgets',
    'PyQt5.sip',
]

# Collect PyQt5 data
tmp_ret = collect_all('PyQt5')
datas += tmp_ret[0]
binaries += tmp_ret[1]
hiddenimports += tmp_ret[2]

a = Analysis(
    ['launcher.py'],
    pathex=['.'],
    binaries=binaries,
    datas=datas,
    hiddenimports=hiddenimports,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[
        'setuptools', 'pip', 'pkg_resources',
        'PyQt5.pylupdate', 'PyQt5.pyrcc', 'PyQt5.uic',
        'PyQt5.QtDesigner', 'PyQt5.QtHelp', 'PyQt5.QtTest',
        'PyQt5.QtDBus', 'PyQt5.QtBluetooth', 'PyQt5.QtNfc',
        'matplotlib', 'numpy', 'scipy', 'music21',
        'librosa', 'networkx', 'sklearn', 'scikit-learn',
        'numba', 'resampy', 'audioread', 'soundfile',
        'PIL', 'cffi', 'lxml',
    ],
    noarchive=False,
)

pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.datas,
    exclude_binaries=True,
    name='TMA Launcher',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=False,
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon='app_icon.icns',
)

app = BUNDLE(
    exe,
    name='TMA Launcher.app',
    icon='app_icon.icns',
    bundle_identifier='com.musicanalysis.tma-launcher',
    info_plist={
        'NSPrincipalClass': 'NSApplication',
        'NSHighResolutionCapable': 'True',
        'CFBundleName': 'TMA Launcher',
        'CFBundleShortVersionString': '1.8.0',
        'CFBundleVersion': '1.8.0',
        'CFBundleInfoDictionaryVersion': '6.0',
        'CFBundlePackageType': 'APPL',
        'LSMinimumSystemVersion': '10.15',
        'NSHumanReadableCopyright': '2025 Yvonne',
    },
)
