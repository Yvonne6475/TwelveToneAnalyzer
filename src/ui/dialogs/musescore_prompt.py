"""MuseScore 4 detection and download guidance dialog."""

import os
import webbrowser
from PyQt5.QtWidgets import (
    QDialog, QVBoxLayout, QLabel, QPushButton, QFileDialog,
    QListWidget, QListWidgetItem, QAbstractItemView,
)
from PyQt5.QtCore import Qt

from src.utils.config import (
    detect_musescore, set_musescore_path, find_all_musescore_installations,
)
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
        self._found = find_all_musescore_installations()
        self._setup_ui()

    def _setup_ui(self):
        self.setWindowTitle(tr("ms.title"))
        self.setMinimumWidth(960)
        self.setMinimumHeight(720)
        self.setWindowFlags(self.windowFlags() & ~Qt.WindowContextHelpButtonHint)

        layout = QVBoxLayout(self)
        layout.setSpacing(16)
        layout.setContentsMargins(40, 32, 40, 32)

        title = QLabel(tr("ms.heading"))
        title.setStyleSheet("font-size: 28px; font-weight: bold;")
        layout.addWidget(title)

        desc = QLabel(tr("ms.desc"))
        desc.setWordWrap(True)
        desc.setStyleSheet("font-size: 18px;")
        layout.addWidget(desc)

        # ── Auto-detected installations (PRIMARY, shown first) ──
        if self._found:
            found_label = QLabel(tr("ms.found_list"))
            found_label.setStyleSheet("font-size: 24px; font-weight: bold; margin-top: 16px;")
            layout.addWidget(found_label)

            self._list = QListWidget()
            self._list.setSelectionMode(QAbstractItemView.SingleSelection)
            self._list.setStyleSheet("font-size: 20px;")
            for p in self._found:
                name = os.path.basename(p)
                item = QListWidgetItem(f"{name}  —  {p}")
                item.setData(Qt.UserRole, p)
                self._list.addItem(item)
            self._list.setCurrentRow(0)
            self._list.setMaximumHeight(min(len(self._found) * 56 + 8, 240))
            layout.addWidget(self._list)

            btn_use = QPushButton(tr("ms.btn_use_detected"))
            btn_use.setMinimumHeight(60)
            btn_use.setStyleSheet(
                "QPushButton { background-color: #4CAF50; color: white; "
                "padding: 16px 24px; font-size: 22px; font-weight: bold; border-radius: 8px; }"
                "QPushButton:hover { background-color: #388E3C; }"
            )
            btn_use.clicked.connect(self._on_use_detected)
            layout.addWidget(btn_use)

        # ── Recommend download ──────────────────────────────────
        btn_download = QPushButton(tr("ms.btn_download"))
        btn_download.setMinimumHeight(64)
        btn_download.setStyleSheet(
            "QPushButton { background-color: #2196F3; color: white; "
            "padding: 20px 28px; font-size: 24px; font-weight: bold; border-radius: 8px; }"
            "QPushButton:hover { background-color: #1976D2; }"
        )
        btn_download.clicked.connect(self._on_download)
        layout.addWidget(btn_download)

        # ── Browse manually ─────────────────────────────────────
        btn_browse = QPushButton(tr("ms.btn_browse"))
        btn_browse.setMinimumHeight(36)
        btn_browse.setStyleSheet(
            "QPushButton { padding: 8px 16px; font-size: 15px; border-radius: 4px; }"
        )
        btn_browse.clicked.connect(self._on_browse)
        layout.addWidget(btn_browse)

        # ── Skip ────────────────────────────────────────────────
        btn_skip = QPushButton(tr("ms.btn_skip"))
        btn_skip.setStyleSheet(
            "QPushButton { padding: 8px 16px; font-size: 15px; border-radius: 4px; "
            "color: #888; border: 1px solid #555; }"
        )
        btn_skip.clicked.connect(self.reject)
        layout.addWidget(btn_skip)

    def _on_download(self):
        webbrowser.open(_musescore_download_url())

    def _on_use_detected(self):
        if hasattr(self, '_list') and self._list.currentItem():
            path = self._list.currentItem().data(Qt.UserRole)
            set_musescore_path(path)
            self._musescore_path = path
            self.accept()

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
