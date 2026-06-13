"""Twelve-Tone Music Analysis Software — Entry Point."""

import sys
import os
import traceback
from pathlib import Path

# ── Fix music21 corpus path in PyInstaller bundle ──────────────────
# music21 uses inspect.getfile() + .parent.parent to locate its corpus
# directory, which resolves incorrectly inside a frozen app. Set the
# manualCoreCorpusPath to point to the bundled corpus data instead.
if getattr(sys, 'frozen', False):
    _bundle_dir = Path(getattr(sys, '_MEIPASS', Path(sys.executable).parent))
    _corpus_path = _bundle_dir / 'music21' / 'corpus'
    if _corpus_path.is_dir():
        # Pre-import music21 environment and set the path before any
        # other music21 imports happen
        try:
            from music21 import environment
            _env = environment.Environment()
            _env['manualCoreCorpusPath'] = str(_corpus_path)
            _env['autoDownload'] = 'allow'
        except Exception:
            pass
    del _bundle_dir, _corpus_path

# ── Fix PyQt5 DLL loading on Windows ──────────────────────────────
# PyQt5 5.15.6+ stores Qt5 DLLs in PyQt5/Qt5/bin/ and the .pyd files
# in PyQt5/ root. On some Windows setups, the DLL loader cannot resolve
# the .pyd → Qt5 DLL dependency chain. The fix: preload Qt5Core/Gui/
# Widgets via ctypes BEFORE any PyQt5 import, so they are already in
# memory when the .pyd files need them.
if sys.platform == 'win32':
    if getattr(sys, 'frozen', False):
        # Packaged by PyInstaller — handled by pyi_rth_qt_dll.py runtime hook
        pass
    else:
        import ctypes
        _candidates = []
        for _p in sys.path:
            _qt_bin = os.path.join(_p, 'PyQt5', 'Qt5', 'bin')
            if os.path.isdir(_qt_bin) and _qt_bin not in _candidates:
                _candidates.append(_qt_bin)
        _local_qt = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                                 '.venv', 'Lib', 'site-packages', 'PyQt5', 'Qt5', 'bin')
        if os.path.isdir(_local_qt) and _local_qt not in _candidates:
            _candidates.append(_local_qt)
        for _d in _candidates:
            try:
                os.add_dll_directory(_d)
            except AttributeError:
                pass
            for _dll in ('Qt5Core.dll', 'Qt5Gui.dll', 'Qt5Widgets.dll'):
                _dll_path = os.path.join(_d, _dll)
                if os.path.isfile(_dll_path):
                    try:
                        ctypes.CDLL(_dll_path)
                    except Exception:
                        pass
        del ctypes, _candidates, _p, _qt_bin, _local_qt, _d, _dll, _dll_path

from PyQt5.QtWidgets import QApplication, QMessageBox
from PyQt5.QtGui import QFont

from src.ui.main_window import MainWindow
from src.ui.theme import apply_theme
from src.ui.dialogs.musescore_prompt import check_musescore_on_startup
from src.utils.config import set_temp_dir, get_temp_dir


def _exception_hook(exctype, value, tb):
    """Global exception hook — shows unhandled errors in a dialog instead of silent crash.

    Critical for packaged EXE where console output is invisible.
    """
    traceback.print_exception(exctype, value, tb)
    QMessageBox.critical(
        None, "Unexpected Error",
        f"{exctype.__name__}: {value}\n\n"
        f"Please report this issue.\n\n"
        f"Traceback:\n{''.join(traceback.format_tb(tb))}"
    )


def main():
    # Install global exception hook early for packaged EXE crash visibility
    sys.excepthook = _exception_hook

    app = QApplication(sys.argv)
    app.setApplicationName("Twelve-Tone Music Analyzer")
    app.setOrganizationName("MusicAnalysis")

    # Set default font
    font = QFont("Segoe UI", 10)
    font.setStyleStrategy(QFont.PreferAntialias)
    app.setFont(font)

    # Apply dark music theme
    apply_theme(app)

    # Ensure temp directory exists
    temp_dir = get_temp_dir()
    os.makedirs(temp_dir, exist_ok=True)
    set_temp_dir(temp_dir)

    # Check MuseScore availability
    musescore_path = check_musescore_on_startup()

    # Create and show main window (centered, reasonable default size)
    window = MainWindow(musescore_path=musescore_path)
    window.resize(1400, 880)
    # Center on screen (use QScreen instead of deprecated QDesktopWidget)
    screen = app.primaryScreen()
    if screen is not None:
        cp = screen.availableGeometry().center()
        qr = window.frameGeometry()
        qr.moveCenter(cp)
        window.move(qr.topLeft())
    window.show()

    sys.exit(app.exec_())


if __name__ == "__main__":
    main()
