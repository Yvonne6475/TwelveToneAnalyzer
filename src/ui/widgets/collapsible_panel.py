"""
Reusable Collapsible Panel widget — cross-platform (Windows + macOS).

A QWidget that provides a title-bar with label + close button, and a
content area that can be toggled visible/hidden via an external button.

Platform-adaptive behaviour
───────────────────────────
- Interaction logic: 100% shared between Windows and macOS.
- Visual tweaks delegated to the caller via stylesheets (font-family,
  border-radius, scrollbar width, etc.).
- On macOS the native Aqua scrollbars are preferred; on Windows custom
  scrollbar CSS is applied.  See src/ui/theme.py for helpers.

Usage
─────
    panel = CollapsiblePanel(title="Row Grouping Controls", parent=self)
    panel.content_layout().addWidget(...)   # add your content
    layout.addWidget(panel)

    # Toggle via an external button
    btn = QPushButton("Open Panel")
    btn.clicked.connect(panel.toggle)
    panel.toggled.connect(lambda visible: btn.setText(
        "Close Panel" if visible else "Open Panel"))
"""

import sys
from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
)
from PyQt5.QtCore import Qt, pyqtSignal


# ── Platform helpers ──────────────────────────────────────────────
IS_MAC = sys.platform == "darwin"
IS_WIN = sys.platform == "win32"


class CollapsiblePanel(QWidget):
    """A collapsible panel with a title bar and content area.

    Signals
    -------
    toggled(bool)
        Emitted when the panel visibility changes.  ``True`` = opened,
        ``False`` = closed.
    """

    toggled = pyqtSignal(bool)

    def __init__(self, title: str = "", parent=None, visible: bool = False):
        """
        Parameters
        ----------
        title : str
            Text displayed in the title bar.
        parent : QWidget, optional
        visible : bool
            Initial visibility.  Default ``False`` (collapsed).
        """
        super().__init__(parent)
        self.setVisible(visible)

        # ── Outer layout ────────────────────────────────────────
        outer = QVBoxLayout(self)
        outer.setContentsMargins(0, 4, 0, 0)
        outer.setSpacing(4)

        # ── Title bar ───────────────────────────────────────────
        title_bar = QHBoxLayout()

        self._title_label = QLabel(title)
        # Platform-adaptive title-bar styling.
        # macOS: slightly smaller radius, no bold background (native feel).
        # Windows: warmer background, visible border-radius.
        if IS_MAC:
            title_style = (
                "font-weight: 600; font-size: 12pt; color: #3a3a3a;"
                "padding: 3px 8px; background: #ececec; border-radius: 3px;"
            )
        else:
            title_style = (
                "font-weight: bold; font-size: 12pt; color: #4a3728;"
                "padding: 4px 8px; background: #e8dcc8; border-radius: 4px;"
            )
        self._title_label.setStyleSheet(title_style)
        title_bar.addWidget(self._title_label)
        title_bar.addStretch()

        self._btn_close = QPushButton("✕")  # ✕
        self._btn_close.setFixedSize(26, 26)
        self._btn_close.setToolTip("Close panel")
        close_style = (
            "QPushButton { font-size: 14px; border: none; background: transparent; }"
            "QPushButton:hover { color: #c0392b; font-weight: bold; }"
        )
        self._btn_close.setStyleSheet(close_style)
        self._btn_close.clicked.connect(self.collapse)
        title_bar.addWidget(self._btn_close)

        outer.addLayout(title_bar)

        # ── Content container ───────────────────────────────────
        self._content = QWidget()
        self._content_layout = QVBoxLayout(self._content)
        self._content_layout.setContentsMargins(0, 0, 0, 0)
        self._content_layout.setSpacing(4)
        outer.addWidget(self._content)

    # ── Public API ───────────────────────────────────────────────

    def content_layout(self) -> QVBoxLayout:
        """Return the layout where callers should add their widgets."""
        return self._content_layout

    def set_title(self, title: str):
        """Update the title bar text."""
        self._title_label.setText(title)

    # ── Toggle / collapse / expand ───────────────────────────────

    def toggle(self):
        """Flip visibility.  Connected buttons should use this slot."""
        if self.isVisible():
            self.collapse()
        else:
            self.expand()

    def collapse(self):
        """Hide the panel."""
        self.setVisible(False)
        self.toggled.emit(False)

    def expand(self):
        """Show the panel."""
        self.setVisible(True)
        self.toggled.emit(True)

    @property
    def is_expanded(self) -> bool:
        return self.isVisible()
