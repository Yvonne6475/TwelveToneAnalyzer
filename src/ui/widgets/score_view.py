"""Score preview widget using music21's show() capabilities."""

from PyQt5.QtWidgets import QWidget, QVBoxLayout, QLabel
from PyQt5.QtCore import Qt

from src.utils.i18n import tr


class ScoreView(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self._layout = QVBoxLayout(self)
        self._label = QLabel(tr("score.no_score"))
        self._label.setAlignment(Qt.AlignCenter)
        self._label.setStyleSheet("color: #888; font-size: 14px;")
        self._layout.addWidget(self._label)

    def set_info(self, text: str):
        self._label.setText(text)

    def clear(self):
        self._label.setText(tr("score.no_score"))
