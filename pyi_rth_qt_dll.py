"""
PyInstaller runtime hook: preload Qt5 DLLs before PyQt5 imports.

Executed by PyInstaller BEFORE main.py to prevent:
    ImportError: DLL load failed while importing QtWidgets

Strategy: add Qt5/bin to DLL search path AND preload three core DLLs
via ctypes so they are already in memory when .pyd files need them.
"""
import os
import sys
import ctypes

_base = sys._MEIPASS

# Directories to add to DLL search
_dirs = [
    os.path.join(_base, 'PyQt5', 'Qt5', 'bin'),                # Qt5 runtime DLLs
    os.path.join(_base, 'PyQt5', 'Qt5', 'plugins', 'platforms'),  # qwindows.dll
    os.path.join(_base, 'PyQt5'),                                # PyQt5 root (.pyd/.dll)
    _base,                                                       # _internal root (fallback)
]

for _d in _dirs:
    if os.path.isdir(_d):
        try:
            os.add_dll_directory(_d)
        except AttributeError:
            pass

# Preload core Qt5 DLLs — forces Windows to resolve them BEFORE any
# PyQt5 .pyd import, fixing the "找不到指定的程序" error caused by
# the .pyd → Qt5 DLL import-table resolution failure on some systems.
_qt_bin = os.path.join(_base, 'PyQt5', 'Qt5', 'bin')
_preloads = [
    os.path.join(_qt_bin, 'Qt5Core.dll'),
    os.path.join(_qt_bin, 'Qt5Gui.dll'),
    os.path.join(_qt_bin, 'Qt5Widgets.dll'),
]
for _dll_path in _preloads:
    if os.path.isfile(_dll_path):
        try:
            ctypes.CDLL(_dll_path)
        except Exception:
            pass

# Set Qt plugin path (belt + suspenders)
_qt_plugins = os.path.join(_base, 'PyQt5', 'Qt5', 'plugins')
if os.path.isdir(_qt_plugins):
    os.environ.setdefault('QT_PLUGIN_PATH', _qt_plugins)

# PATH for subprocess DLL resolution (MuseScore, etc.)
os.environ['PATH'] = os.pathsep.join(
    [d for d in _dirs if os.path.isdir(d)] + [os.environ.get('PATH', '')]
)

# Clean up module-level names
del _base, _dirs, _d, _qt_bin, _preloads, _dll_path, _qt_plugins
