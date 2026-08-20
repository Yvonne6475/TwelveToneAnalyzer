# -*- mode: python ; coding: utf-8 -*-
"""PyInstaller spec for TMA Auto-Updating Launcher — Windows.

Tiny standalone EXE (~25 MB) that git-clones the full app on first run
and does incremental git-pull updates on every restart.
"""

datas = []
binaries = []
hiddenimports = ['PyQt5', 'PyQt5.QtCore', 'PyQt5.QtGui', 'PyQt5.QtWidgets', 'PyQt5.sip']

datas = []
binaries = []
hiddenimports = [
    'matplotlib.backends.backend_qt5agg',
    'PyQt5.sip',
    'PyQt5',
    'PyQt5.QtCore',
    'PyQt5.QtGui',
    'PyQt5.QtWidgets',
]

from PyInstaller.utils.hooks import collect_dynamic_libs, collect_all
binaries += collect_dynamic_libs('PyQt5')

tmp_ret = collect_all('PyQt5')
def _keep_qt_binary(bin_src, bin_dest):
    name = __import__('os').path.basename(bin_src)
    _exclude = {'Qt5Designer', 'Qt5Help', 'Qt5Test', 'Qt5DBus', 'Qt5Bluetooth',
                'Qt5Nfc', 'Qt5Sql', 'Qt5SerialPort', 'Qt5Sensors', 'Qt5Location',
                'Qt5RemoteObjects', 'Qt5WebChannel', 'Qt5WebSockets',
                'Qt5XmlPatterns', 'Qt5TextToSpeech', 'Qt5WinExtras',
                'Qt5Quick3D', 'Qt5QuickTest', 'Qt5Positioning',
                'Qt5Multimedia', 'Qt5MultimediaWidgets'}
    for dll in _exclude:
        if name.startswith(dll):
            return False
    return '/qml/' not in bin_dest.replace('\\', '/').lower()

def _keep_qt_data(data_path):
    lower = data_path.replace('\\', '/').lower()
    if '/uic/' in lower or '/pylupdate' in lower or '/pyrcc' in lower:
        return False
    return '/qml/' not in lower

datas += [(s, d) for (s, d) in tmp_ret[0] if _keep_qt_data(s)]
binaries += [(s, d) for (s, d) in tmp_ret[1] if _keep_qt_binary(s, d)]
hiddenimports += tmp_ret[2]

# Bundle Python DLL
import sys
_py_dll_name = f'python{sys.version_info.major}{sys.version_info.minor}.dll'
_py_dll_path = None
for _d in [sys.prefix, __import__('os').path.dirname(sys.executable)]:
    _candidate = __import__('os').path.join(_d, _py_dll_name)
    if __import__('os').path.exists(_candidate):
        _py_dll_path = _candidate
        break
if _py_dll_path:
    binaries += [(_py_dll_path, '.')]

a = Analysis(
    ['launcher.py'],
    pathex=['.'],
    binaries=binaries,
    datas=datas + [('resources/', 'resources'), ('assets/', 'assets')],
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
    [],
    exclude_binaries=True,
    name='TMA_Launcher',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    console=False,
    disable_windowed_traceback=True,
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
    name='TMA_Launcher',
)
