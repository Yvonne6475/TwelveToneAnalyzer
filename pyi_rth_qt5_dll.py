import os, sys
_qt_bin = os.path.join(sys._MEIPASS, 'PyQt5', 'Qt5', 'bin')
if os.path.isdir(_qt_bin):
    try:
        os.add_dll_directory(_qt_bin)
    except AttributeError:
        os.environ['PATH'] = _qt_bin + os.pathsep + os.environ.get('PATH', '')
if sys.platform == 'win32':
    try:
        os.add_dll_directory(sys._MEIPASS)
    except AttributeError:
        pass
