"""Image viewer first-run configuration dialog."""

import os
import webbrowser
import glob
from PyQt5.QtWidgets import (
    QDialog, QVBoxLayout, QLabel, QPushButton, QFileDialog, QListWidget,
    QListWidgetItem, QAbstractItemView,
)
from PyQt5.QtCore import Qt

from src.utils.config import get_image_viewer_path, set_image_viewer_path
from src.utils.i18n import tr, current_language


BANDIVIEW_DOWNLOAD = "https://www.bandisoft.com/bandiview/"

_VIEWER_CANDIDATES = [
    # BandiView
    r"D:\Program Files (x86)\BandiView\BandiView.exe",
    r"C:\Program Files\BandiView\BandiView.exe",
    r"C:\Program Files (x86)\BandiView\BandiView.exe",
    # Honeyview (same vendor, free)
    r"C:\Program Files\Honeyview\Honeyview.exe",
    r"D:\Program Files\Honeyview\Honeyview.exe",
    # IrfanView
    r"C:\Program Files\IrfanView\i_view64.exe",
    r"C:\Program Files (x86)\IrfanView\i_view32.exe",
    # ImageGlass
    r"C:\Program Files\ImageGlass\ImageGlass.exe",
    # FastStone
    r"C:\Program Files (x86)\FastStone Image Viewer\FSViewer.exe",
    r"C:\Program Files\FastStone Image Viewer\FSViewer.exe",
    # XnView
    r"C:\Program Files\XnView\xnview.exe",
    r"C:\Program Files (x86)\XnView\xnview.exe",
    # Built-in Windows
    os.path.expandvars(r"${LOCALAPPDATA}\Microsoft\WindowsApps\mspaint.exe"),
]


def find_all_viewers() -> list[str]:
    """Return paths to all installed PNG viewers found on this system."""
    found = []
    seen = set()
    for pattern in _VIEWER_CANDIDATES:
        if '*' in pattern:
            for p in glob.glob(pattern):
                if os.path.isfile(p) and p not in seen:
                    found.append(p)
                    seen.add(p)
        elif os.path.isfile(pattern) and pattern not in seen:
            found.append(pattern)
            seen.add(pattern)
    return found


class ImageViewerPromptDialog(QDialog):
    """First-run dialog: recommend BandiView, auto-detect viewers, or browse."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self._viewer_path = ""
        self._found_viewers = find_all_viewers()
        self._setup_ui()

    def _setup_ui(self):
        self.setWindowTitle(tr("iv.title"))
        self.setMinimumWidth(960)
        self.setMinimumHeight(720)
        self.setWindowFlags(self.windowFlags() & ~Qt.WindowContextHelpButtonHint)

        layout = QVBoxLayout(self)
        layout.setSpacing(16)
        layout.setContentsMargins(40, 32, 40, 32)

        title = QLabel(tr("iv.heading"))
        title.setStyleSheet("font-size: 28px; font-weight: bold;")
        layout.addWidget(title)

        desc = QLabel(tr("iv.desc"))
        desc.setWordWrap(True)
        desc.setStyleSheet("font-size: 18px;")
        layout.addWidget(desc)

        # ── Auto-detected viewers (PRIMARY, shown first) ───────
        if self._found_viewers:
            found_label = QLabel(tr("iv.found_list"))
            found_label.setStyleSheet("font-size: 24px; font-weight: bold; margin-top: 16px;")
            layout.addWidget(found_label)

            self._list = QListWidget()
            self._list.setSelectionMode(QAbstractItemView.SingleSelection)
            self._list.setStyleSheet("font-size: 20px;")
            for p in self._found_viewers:
                name = os.path.basename(p)
                item = QListWidgetItem(f"{name}  —  {p}")
                item.setData(Qt.UserRole, p)
                self._list.addItem(item)
            self._list.setCurrentRow(0)
            self._list.setMaximumHeight(min(len(self._found_viewers) * 56 + 8, 240))
            layout.addWidget(self._list)

            btn_use_found = QPushButton(tr("iv.btn_use_selected"))
            btn_use_found.setMinimumHeight(60)
            btn_use_found.setStyleSheet(
                "QPushButton { background-color: #4CAF50; color: white; "
                "padding: 16px 24px; font-size: 22px; font-weight: bold; border-radius: 8px; }"
                "QPushButton:hover { background-color: #388E3C; }"
            )
            btn_use_found.clicked.connect(self._on_use_selected)
            layout.addWidget(btn_use_found)

        # ── Recommend BandiView ────────────────────────────────
        btn_download = QPushButton(tr("iv.btn_download"))
        btn_download.setMinimumHeight(64)
        btn_download.setStyleSheet(
            "QPushButton { background-color: #2196F3; color: white; "
            "padding: 20px 28px; font-size: 24px; font-weight: bold; border-radius: 8px; }"
            "QPushButton:hover { background-color: #1976D2; }"
        )
        btn_download.clicked.connect(self._on_download)
        layout.addWidget(btn_download)

        # ── Browse manually ────────────────────────────────────
        btn_browse = QPushButton(tr("iv.btn_browse"))
        btn_browse.setMinimumHeight(36)
        btn_browse.setStyleSheet(
            "QPushButton { padding: 8px 16px; font-size: 15px; border-radius: 4px; }"
        )
        btn_browse.clicked.connect(self._on_browse)
        layout.addWidget(btn_browse)

        # ── Skip ───────────────────────────────────────────────
        btn_skip = QPushButton(tr("iv.btn_skip"))
        btn_skip.setStyleSheet(
            "QPushButton { padding: 8px 16px; font-size: 15px; border-radius: 4px; "
            "color: #888; border: 1px solid #555; }"
        )
        btn_skip.clicked.connect(self.reject)
        layout.addWidget(btn_skip)

    def _on_download(self):
        webbrowser.open(BANDIVIEW_DOWNLOAD)
        # Don't close — user might want to browse after installing

    def _on_use_selected(self):
        if hasattr(self, '_list') and self._list.currentItem():
            path = self._list.currentItem().data(Qt.UserRole)
            set_image_viewer_path(path)
            self._viewer_path = path
            self.accept()

    def _on_browse(self):
        path, _ = QFileDialog.getOpenFileName(
            self, tr("iv.browse_title"),
            r"C:\Program Files",
            tr("iv.browse_filter"),
        )
        if path:
            set_image_viewer_path(path)
            self._viewer_path = path
            self.accept()

    def viewer_path(self) -> str:
        return self._viewer_path


def check_image_viewer_on_startup(parent=None) -> str:
    """Check if image viewer is configured; prompt on first run if not."""
    configured = get_image_viewer_path()
    if configured and os.path.isfile(configured):
        return configured

    dialog = ImageViewerPromptDialog(parent)
    dialog.exec_()
    return dialog.viewer_path()