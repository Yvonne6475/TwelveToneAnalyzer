"""Configuration management with QSettings persistence and MuseScore detection."""
from __future__ import annotations

import os
import sys
import tempfile
from pathlib import Path
from PyQt5.QtCore import QSettings


ORGANIZATION = "MusicAnalysis"
APPLICATION = "TwelveToneAnalyzer"


def resource_path(relative_path: str) -> str:
    """Get absolute path to a resource file.

    Works for both development and PyInstaller-packaged builds.
    When packaged, sys._MEIPASS points to the temp extraction directory.
    """
    if getattr(sys, 'frozen', False):
        base_path: str = sys._MEIPASS
    else:
        base_path = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    return os.path.join(base_path, relative_path)

MUSESCORE_WIN_PATHS = [
    r"C:\Program Files\MuseScore 4\bin\MuseScore4.exe",
    r"C:\Program Files (x86)\MuseScore 4\bin\MuseScore4.exe",
    r"C:\Program Files\MuseScore 4\MuseScore4.exe",
    r"C:\Program Files (x86)\MuseScore 4\MuseScore4.exe",
]

MUSESCORE_MAC_PATHS = [
    "/Applications/MuseScore 4.app/Contents/MacOS/mscore",
]


def _search_program_files(pattern: str) -> list[str]:
    """Scan Program Files directories for executables matching pattern."""
    import glob as _glob
    results = []
    for root in [r"C:\Program Files", r"C:\Program Files (x86)",
                 r"D:\Program Files", r"D:\Program Files (x86)"]:
        try:
            for p in _glob.glob(fr"{root}\{pattern}", recursive=True):
                if os.path.isfile(p) and p not in results:
                    results.append(p)
        except Exception:
            pass
    return results


def get_settings() -> QSettings:
    return QSettings(ORGANIZATION, APPLICATION)


def get_musescore_path() -> str:
    """Return configured MuseScore path, or auto-detect, or empty string."""
    settings = get_settings()
    configured = settings.value("musescore/path", "", type=str)
    if configured and os.path.isfile(configured):
        return configured
    return _auto_detect_musescore() or configured


def set_musescore_path(path: str):
    get_settings().setValue("musescore/path", path)


def _is_writable_dir(path: str) -> bool:
    """Return True if `path` exists (or can be created) and is writable."""
    if not path:
        return False
    try:
        os.makedirs(path, exist_ok=True)
        fd, probe = tempfile.mkstemp(prefix="tta_probe_", dir=path)
        os.close(fd)
        os.remove(probe)
        return True
    except Exception:
        return False


def _default_temp_dir() -> str:
    """Default temp dir: Windows → D:\\TwelveToneAnalyzer; macOS → ~/MusicAnalysisTemp."""
    if sys.platform == 'win32':
        d_drive = r"D:\TwelveToneAnalyzer"
        if _is_writable_dir(d_drive):
            return d_drive
    return str(Path.home() / "MusicAnalysisTemp")


def get_temp_dir() -> str:
    settings = get_settings()
    default = _default_temp_dir()
    configured = settings.value("general/temp_dir", default, type=str)
    if _is_writable_dir(configured):
        return configured

    os.makedirs(default, exist_ok=True)
    settings.setValue("general/temp_dir", default)
    return default


def set_temp_dir(path: str):
    if not _is_writable_dir(path):
        raise OSError(f"Temp directory is not writable: {path}")
    get_settings().setValue("general/temp_dir", path)


def temp_default_path(filename: str) -> str:
    """Return a default save path inside the user's configured temp directory."""
    return os.path.join(get_temp_dir(), filename)


def configure_music21_environment():
    """Sync music21 scratch directory and MuseScore path with current config."""
    try:
        from music21 import environment
        env = environment.Environment()
        temp_dir = get_temp_dir()
        env['directoryScratch'] = temp_dir

        ms_path = get_musescore_path()
        if ms_path and os.path.isfile(ms_path):
            env['musicxmlPath'] = ms_path
            env['musescoreDirectPNGPath'] = ms_path
    except Exception:
        pass


def detect_musescore() -> tuple:
    """Detect MuseScore 4 installation.
    Returns ('found', path) or ('not_found', None).
    """
    # Check configured path first
    configured = get_settings().value("musescore/path", "", type=str)
    if configured and os.path.isfile(configured):
        return ("found", configured)

    # Auto-detect
    auto_path = _auto_detect_musescore()
    if auto_path:
        return ("found", auto_path)
    return ("not_found", None)


def find_all_musescore_installations() -> list[str]:
    """Return all MuseScore executable paths found on this system."""
    if sys.platform == "win32":
        found = [p for p in MUSESCORE_WIN_PATHS if os.path.isfile(p)]
        # Also search broadly under Program Files
        broad = _search_program_files(r"MuseScore*\**\MuseScore4.exe")
        for p in broad:
            if p not in found:
                found.append(p)
        return found
    elif sys.platform == "darwin":
        return [p for p in MUSESCORE_MAC_PATHS if os.path.isfile(p)]
    return []


def _auto_detect_musescore() -> str | None:
    found = find_all_musescore_installations()
    return found[0] if found else None


def show_score(stream, fmt='musicxml', parent=None):
    """Show a music21 Stream in MuseScore (or system default handler).

    Replaces stream.show() which uses subprocess.run(['open', ...]) —
    unreliable inside PyInstaller-frozen macOS apps.

    Writes the stream to a temp file, then opens it with the configured
    MuseScore (if available) or the system default application.
    """
    import subprocess
    import tempfile
    from PyQt5.QtCore import QUrl
    from PyQt5.QtGui import QDesktopServices

    ms_path = get_musescore_path()
    temp_dir = get_temp_dir()
    os.makedirs(temp_dir, exist_ok=True)

    fd, tmp_path = tempfile.mkstemp(suffix='.musicxml', dir=temp_dir)
    os.close(fd)

    try:
        stream.write(fmt, tmp_path)
    except Exception:
        os.remove(tmp_path)
        raise

    if ms_path and os.path.isfile(ms_path):
        # Open directly with configured MuseScore
        try:
            subprocess.Popen([ms_path, tmp_path])
        except Exception:
            QDesktopServices.openUrl(QUrl.fromLocalFile(tmp_path))
    else:
        QDesktopServices.openUrl(QUrl.fromLocalFile(tmp_path))


def get_image_viewer_path() -> str:
    """Return the user-configured image viewer path, or empty string."""
    return get_settings().value("windows/image_viewer", "", type=str)


def set_image_viewer_path(path: str):
    """Save the user-configured image viewer path."""
    get_settings().setValue("windows/image_viewer", path)
