"""First-run temp directory configuration dialog."""

import os
from pathlib import Path
from PyQt5.QtWidgets import (
    QDialog, QVBoxLayout, QLabel, QPushButton, QFileDialog,
)
from PyQt5.QtCore import Qt

from src.utils.config import get_temp_dir, set_temp_dir, get_settings, _default_temp_dir
from src.utils.i18n import tr


class TempDirPromptDialog(QDialog):
    """First-run dialog: let user choose where temp/export files go."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self._temp_path = ""
        self._setup_ui()

    def _setup_ui(self):
        self.setWindowTitle(tr("td.title"))
        self.setMinimumWidth(800)
        self.setMinimumHeight(480)

        layout = QVBoxLayout(self)
        layout.setSpacing(16)
        layout.setContentsMargins(40, 32, 40, 32)

        title = QLabel(tr("td.heading"))
        title.setStyleSheet("font-size: 28px; font-weight: bold;")
        layout.addWidget(title)

        desc = QLabel(tr("td.desc"))
        desc.setWordWrap(True)
        desc.setStyleSheet("font-size: 18px;")
        layout.addWidget(desc)

        # Default path preview
        default_path = _default_temp_dir()
        self._default_label = QLabel(
            tr("td.default_path", path=default_path)
        )
        self._default_label.setWordWrap(True)
        self._default_label.setStyleSheet(
            "font-size: 18px; color: #aaa; padding: 8px; border: 1px solid #555; border-radius: 4px;"
        )
        layout.addWidget(self._default_label)

        layout.addStretch()

        # Use default
        btn_default = QPushButton(tr("td.btn_default"))
        btn_default.setMinimumHeight(56)
        btn_default.setStyleSheet(
            "QPushButton { background-color: #4CAF50; color: white; "
            "padding: 16px 24px; font-size: 20px; font-weight: bold; border-radius: 8px; }"
            "QPushButton:hover { background-color: #388E3C; }"
        )
        btn_default.clicked.connect(self._on_use_default)
        layout.addWidget(btn_default)

        # Custom folder
        btn_custom = QPushButton(tr("td.btn_custom"))
        btn_custom.setMinimumHeight(48)
        btn_custom.setStyleSheet(
            "QPushButton { background-color: #2196F3; color: white; "
            "padding: 14px 20px; font-size: 18px; font-weight: bold; border-radius: 6px; }"
            "QPushButton:hover { background-color: #1976D2; }"
        )
        btn_custom.clicked.connect(self._on_custom)
        layout.addWidget(btn_custom)

    def _on_use_default(self):
        default_path = _default_temp_dir()
        os.makedirs(default_path, exist_ok=True)
        set_temp_dir(default_path)
        self._temp_path = default_path
        self.accept()

    def _on_custom(self):
        path = QFileDialog.getExistingDirectory(
            self, tr("td.browse_title"),
            str(Path.home()),
        )
        if path:
            try:
                os.makedirs(path, exist_ok=True)
                set_temp_dir(path)
                self._temp_path = path
                self.accept()
            except OSError:
                pass  # Keep dialog open, user can retry

    def reject(self):
        """User closed window — accept with empty (caller uses default)."""
        super().reject()

    def temp_path(self) -> str:
        return self._temp_path


def check_temp_dir_on_startup(parent=None) -> str:
    """Ensure temp directory is configured; prompt on first run."""
    configured = get_settings().value("general/temp_dir", "", type=str)
    if not configured:
        dialog = TempDirPromptDialog(parent)
        if dialog.exec_() == QDialog.Rejected or not dialog.temp_path():
            # User closed without choosing — use default
            default_path = _default_temp_dir()
            os.makedirs(default_path, exist_ok=True)
            set_temp_dir(default_path)
            return default_path
        return dialog.temp_path()
    return configured