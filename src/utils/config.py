"""Configuration management with QSettings persistence and MuseScore detection."""
from __future__ import annotations

import os
import sys
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
    r"D:\Program Files (x86)\bin\MuseScore4.exe",
    r"C:\Program Files (x86)\MuseScore 4\bin\MuseScore4.exe",
    r"C:\Program Files\MuseScore 4\MuseScore4.exe",
]

MUSESCORE_MAC_PATHS = [
    "/Applications/MuseScore 4.app/Contents/MacOS/mscore",
]


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


def get_temp_dir() -> str:
    settings = get_settings()
    default = str(Path.home() / "MusicAnalysisTemp")
    return settings.value("general/temp_dir", default, type=str)


def set_temp_dir(path: str):
    get_settings().setValue("general/temp_dir", path)


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


def _auto_detect_musescore() -> str | None:
    if sys.platform == "win32":
        paths = MUSESCORE_WIN_PATHS
    elif sys.platform == "darwin":
        paths = MUSESCORE_MAC_PATHS
    else:
        return None

    for p in paths:
        if os.path.isfile(p):
            return p
    return None
