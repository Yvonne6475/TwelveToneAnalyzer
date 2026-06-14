"""MuseScore 4 detection and download guidance dialog."""

import webbrowser
from PyQt5.QtWidgets import (
    QDialog, QVBoxLayout, QLabel, QPushButton, QHBoxLayout, QFileDialog,
)
from PyQt5.QtCore import Qt

from src.utils.config import detect_musescore, set_musescore_path
from src.utils.i18n import tr, current_language

MUSESCORE_DOWNLOAD_URLS = {
    "zh": "https://musescore.org/zh-hans/download",
    "en": "https://musescore.org/en/download",
}


def _musescore_download_url() -> str:
    return MUSESCORE_DOWNLOAD_URLS.get(current_language(), MUSESCORE_DOWNLOAD_URLS["en"])


class MuseScorePromptDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self._musescore_path = ""
        self._setup_ui()

    def _setup_ui(self):
        self.setWindowTitle(tr("ms.title"))
        self.setMinimumWidth(480)
        self.setWindowFlags(self.windowFlags() & ~Qt.WindowContextHelpButtonHint)

        layout = QVBoxLayout(self)
        layout.setSpacing(16)

        title = QLabel(tr("ms.heading"))
        title.setStyleSheet("font-size: 16px; font-weight: bold;")
        layout.addWidget(title)

        desc = QLabel(tr("ms.desc"))
        desc.setWordWrap(True)
        layout.addWidget(desc)

        btn_download = QPushButton(tr("ms.btn_download"))
        btn_download.setStyleSheet(
            "QPushButton { background-color: #2196F3; color: white; "
            "padding: 10px; font-size: 14px; border-radius: 4px; }"
            "QPushButton:hover { background-color: #1976D2; }"
        )
        btn_download.clicked.connect(self._on_download)
        layout.addWidget(btn_download)

        btn_browse = QPushButton(tr("ms.btn_browse"))
        btn_browse.clicked.connect(self._on_browse)
        layout.addWidget(btn_browse)

        btn_skip = QPushButton(tr("ms.btn_skip"))
        btn_skip.clicked.connect(self.reject)
        layout.addWidget(btn_skip)

    def _on_download(self):
        webbrowser.open(_musescore_download_url())
        self.reject()

    def _on_browse(self):
        path, _ = QFileDialog.getOpenFileName(
            self, tr("ms.browse_title"), "",
            "MuseScore (MuseScore4.exe mscore);;All Files (*)"
        )
        if path:
            set_musescore_path(path)
            self._musescore_path = path
            self.accept()

    def musescore_path(self) -> str:
        return self._musescore_path


def check_musescore_on_startup(parent=None) -> str:
    status, path = detect_musescore()
    if status == "found":
        return path
    dialog = MuseScorePromptDialog(parent)
    dialog.exec_()
    return dialog.musescore_path()
