# -*- mode: python ; coding: utf-8 -*-
from PyInstaller.utils.hooks import collect_dynamic_libs
from PyInstaller.utils.hooks import collect_all

datas = []
binaries = []
hiddenimports = ['matplotlib.backends.backend_qt5agg', 'PyQt5.sip', 'matplotlib.pyplot',
    # music21 format parsers
    'music21.mei', 'music21.mei.base', 'music21.mei.translate',
    'music21.midi', 'music21.midi.translate',
    'music21.musicxml', 'music21.musicxml.xmlToM21', 'music21.musicxml.m21ToXml',
    'music21.abcFormat', 'music21.abcFormat.translate',
    'music21.humdrum', 'music21.humdrum.spineParser',
    'music21.converter.subConverters',
    'music21.graph', 'music21.graph.plot', 'music21.graph.utilities',
    'music21.lily', 'music21.lily.translate',
    'music21.analysis', 'music21.analysis.discrete',
    'librosa', 'scipy.interpolate', 'scipy.signal', 'numpy']
binaries += collect_dynamic_libs('PyQt5')
tmp_ret = collect_all('PyQt5')
# Collect all from scipy so C extensions like _cdflib are bundled
tmp_ret2 = collect_all('scipy')
datas += tmp_ret2[0]; binaries += tmp_ret2[1]; hiddenimports += tmp_ret2[2]
# Filter Qt dev-tool data (uic, pylupdate, pyrcc) and unused-module DLLs
# so they are not packaged.  Runtime-only Qt modules (Core/Gui/Widgets/
# Network/PrintSupport/Svg/OpenGL) are kept.
_qt_exclude_dll = {
    'Qt5Designer', 'Qt5Help', 'Qt5Test', 'Qt5DBus',
    'Qt5Bluetooth', 'Qt5Nfc', 'Qt5Sql', 'Qt5SerialPort',
    'Qt5Sensors', 'Qt5Location', 'Qt5RemoteObjects', 'Qt5WebChannel',
    'Qt5WebSockets', 'Qt5XmlPatterns', 'Qt5TextToSpeech', 'Qt5WinExtras',
    'Qt5Quick3D', 'Qt5QuickTest', 'Qt5Positioning',
    'Qt5Multimedia', 'Qt5MultimediaWidgets',
}
def _keep_qt_binary(bin_src, bin_dest):
    """Exclude unused Qt module DLLs and QML plugins."""
    name = os.path.basename(bin_src)
    for dll in _qt_exclude_dll:
        if name.startswith(dll):
            return False
    dest_lower = bin_dest.replace('\\', '/').lower()
    if '/qml/' in dest_lower:
        return False
    return True

def _keep_qt_data(data_path):
    """Exclude uic/, pyrcc, pylupdate and QML source trees from packaging."""
    lower = data_path.replace('\\', '/').lower()
    if '/uic/' in lower or '/pylupdate' in lower or '/pyrcc' in lower:
        return False
    if '/qml/' in lower:
        return False
    return True

datas += [(s, d) for (s, d) in tmp_ret[0] if _keep_qt_data(s)]
binaries += [(s, d) for (s, d) in tmp_ret[1] if _keep_qt_binary(s, d)]
hiddenimports += tmp_ret[2]
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
    runtime_hooks=['pyi_rth_qt_dll.py', 'pyi_rth_music21.py'],
    excludes=[
        # Qt dev / build tools — not needed at runtime
        'PyQt5.pylupdate', 'PyQt5.pylupdate_main',
        'PyQt5.pyrcc', 'PyQt5.pyrcc_main',
        'PyQt5.uic',
        'PyQt5.QtDesigner',
        'PyQt5.QtHelp',
        'PyQt5.QtTest',
        'PyQt5.QtDBus',
        # Unused Qt modules — safe to exclude, reduce package size
        'PyQt5.QtBluetooth', 'PyQt5.QtNfc',
        'PyQt5.QtSql', 'PyQt5.QtSerialPort',
        'PyQt5.QtSensors', 'PyQt5.QtLocation',
        'PyQt5.QtRemoteObjects', 'PyQt5.QtWebChannel',
        'PyQt5.QtWebSockets', 'PyQt5.QtXmlPatterns',
        'PyQt5.QtTextToSpeech', 'PyQt5.QtWinExtras',
        'PyQt5.QtQuick3D', 'PyQt5.QtQuickTest',
        'PyQt5.QtPositioning',
        'PyQt5.QAxContainer',
    ],
    noarchive=False,
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
)
# Strip QML files regardless of how they got collected (3-tuple TOC format)
a.datas = [t for t in a.datas if '/qml/' not in t[1].replace('\\', '/').lower()]
a.binaries = [t for t in a.binaries if '/qml/' not in t[1].replace('\\', '/').lower()]

coll = COLLECT(
    exe,
    a.binaries,
    a.datas,
    strip=False,
    upx=True,
    upx_exclude=[],
    name='TwelveToneAnalyzer',
)
