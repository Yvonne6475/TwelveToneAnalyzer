"""Settings dialog for MuseScore path, temp directory, and font size."""

import os
from PyQt5.QtWidgets import (
    QDialog, QVBoxLayout, QFormLayout, QLineEdit, QPushButton,
    QHBoxLayout, QFileDialog, QGroupBox, QSpinBox, QLabel,
)
from PyQt5.QtCore import Qt

from src.utils.config import get_musescore_path, set_musescore_path, get_temp_dir, set_temp_dir
from src.ui.theme import get_font_size, set_font_size
from src.utils.i18n import tr


class SettingsDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self._setup_ui()

    def _setup_ui(self):
        self.setWindowTitle(tr("settings.title"))
        self.setMinimumWidth(520)
        self.setWindowFlags(self.windowFlags() & ~Qt.WindowContextHelpButtonHint)

        layout = QVBoxLayout(self)
        layout.setSpacing(12)

        # Font size
        font_group = QGroupBox(tr("settings.font_group"))
        font_layout = QHBoxLayout(font_group)
        font_layout.addWidget(QLabel(tr("settings.font_size")))
        self.font_spin = QSpinBox()
        self.font_spin.setMinimum(9)
        self.font_spin.setMaximum(18)
        self.font_spin.setValue(get_font_size())
        self.font_spin.setSuffix(" pt")
        font_layout.addWidget(self.font_spin)
        font_layout.addStretch()
        layout.addWidget(font_group)

        # MuseScore path
        ms_group = QGroupBox(tr("settings.ms_group"))
        ms_layout = QFormLayout(ms_group)
        self.ms_edit = QLineEdit(get_musescore_path())
        self.ms_edit.setPlaceholderText(tr("settings.ms_placeholder"))
        ms_browse = QHBoxLayout()
        ms_browse.addWidget(self.ms_edit)
        btn_browse = QPushButton(tr("settings.browse"))
        btn_browse.clicked.connect(self._browse_musescore)
        ms_browse.addWidget(btn_browse)
        ms_layout.addRow(tr("settings.ms_label"), ms_browse)
        layout.addWidget(ms_group)

        # Temp directory
        temp_group = QGroupBox(tr("settings.temp_group"))
        temp_layout = QFormLayout(temp_group)
        self.temp_edit = QLineEdit(get_temp_dir())
        temp_browse = QHBoxLayout()
        temp_browse.addWidget(self.temp_edit)
        btn_temp = QPushButton(tr("settings.browse"))
        btn_temp.clicked.connect(self._browse_temp)
        temp_browse.addWidget(btn_temp)
        temp_layout.addRow(tr("settings.temp_label"), temp_browse)
        layout.addWidget(temp_group)

        # Buttons
        btn_layout = QHBoxLayout()
        btn_layout.addStretch()
        btn_save = QPushButton(tr("settings.save"))
        btn_save.clicked.connect(self._on_save)
        btn_layout.addWidget(btn_save)
        btn_cancel = QPushButton(tr("settings.cancel"))
        btn_cancel.clicked.connect(self.reject)
        btn_layout.addWidget(btn_cancel)
        layout.addLayout(btn_layout)

    def _browse_musescore(self):
        path, _ = QFileDialog.getOpenFileName(
            self, tr("settings.browse_ms"), "",
            "MuseScore (MuseScore4.exe mscore);;All Files (*)"
        )
        if path:
            self.ms_edit.setText(path)

    def _browse_temp(self):
        path = QFileDialog.getExistingDirectory(self, tr("settings.browse_temp"))
        if path:
            self.temp_edit.setText(path)

    def _on_save(self):
        ms_path = self.ms_edit.text().strip()
        if ms_path and os.path.isfile(ms_path):
            set_musescore_path(ms_path)
        temp = self.temp_edit.text().strip()
        if temp:
            os.makedirs(temp, exist_ok=True)
            set_temp_dir(temp)
        set_font_size(self.font_spin.value())
        self.accept()
