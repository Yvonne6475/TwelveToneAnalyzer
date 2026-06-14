"""
Update notification and download dialog.

Shows version info, release notes, and manages the download of the
new installer package.  Cross-platform — selects .exe (Win) or .dmg (Mac)
based on the asset URL from GitHub Releases.
"""

import os
import sys
import webbrowser

from PyQt5.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QTextEdit, QProgressBar, QMessageBox, QApplication, QFileDialog,
)
from PyQt5.QtCore import Qt, QThread, pyqtSignal, QObject

from src.core.updater import UpdateInfo, VERSION
from src.utils.i18n import tr


# ── Background download worker ────────────────────────────────────
class _DownloadWorker(QObject):
    progress = pyqtSignal(int)          # percent 0–100
    finished = pyqtSignal(str)          # saved file path
    error = pyqtSignal(str)             # error message

    def __init__(self, url: str, save_path: str):
        super().__init__()
        self._url = url
        self._save_path = save_path
        self._cancelled = False

    def cancel(self):
        self._cancelled = True

    def run(self):
        import urllib.request
        try:
            req = urllib.request.Request(
                self._url,
                headers={"User-Agent": "TwelveToneAnalyzer-Update/1.0"},
            )
            with urllib.request.urlopen(req) as resp:
                total = int(resp.headers.get("Content-Length", 0))
                downloaded = 0
                chunk_size = 8192
                with open(self._save_path, "wb") as f:
                    while True:
                        if self._cancelled:
                            return
                        chunk = resp.read(chunk_size)
                        if not chunk:
                            break
                        f.write(chunk)
                        downloaded += len(chunk)
                        if total > 0:
                            pct = int(downloaded * 100 / total)
                            self.progress.emit(pct)
            if not self._cancelled:
                self.finished.emit(self._save_path)
        except Exception as e:
            if not self._cancelled:
                self.error.emit(str(e))


# ── Update dialog ─────────────────────────────────────────────────
class UpdateDialog(QDialog):
    """Shows update info and manages download + install flow."""

    def __init__(self, info: UpdateInfo, parent=None):
        super().__init__(parent)
        self._info = info
        self._thread = None
        self._worker = None
        self._downloaded_path = ""
        self._setup_ui()

    def _setup_ui(self):
        self.setWindowTitle(tr("update.title"))
        self.setMinimumWidth(500)
        self.setMaximumWidth(620)
        self.setWindowFlags(self.windowFlags() & ~Qt.WindowContextHelpButtonHint)

        layout = QVBoxLayout(self)
        layout.setSpacing(12)

        # ── Heading ────────────────────────────────────────────
        heading = QLabel(tr("update.heading", version=self._info.latest_version))
        heading.setStyleSheet("font-size: 16pt; font-weight: bold; color: #4a3728;")
        heading.setWordWrap(True)
        layout.addWidget(heading)

        # ── Current version ────────────────────────────────────
        current = QLabel(tr("update.current", current=VERSION))
        current.setStyleSheet("color: #888;")
        layout.addWidget(current)

        # ── File size ──────────────────────────────────────────
        if self._info.download_size > 0:
            size_mb = self._info.download_size / (1024 * 1024)
            size_label = QLabel(tr("update.size", size=f"{size_mb:.1f} MB"))
            size_label.setStyleSheet("color: #888;")
            layout.addWidget(size_label)

        # ── Release notes ──────────────────────────────────────
        if self._info.release_notes.strip():
            layout.addWidget(QLabel(tr("update.desc_label")))
            notes = QTextEdit()
            notes.setReadOnly(True)
            notes.setMarkdown(self._info.release_notes)
            notes.setMinimumHeight(120)
            notes.setMaximumHeight(250)
            layout.addWidget(notes)

        # ── Progress bar (hidden initially) ────────────────────
        self._progress = QProgressBar()
        self._progress.setVisible(False)
        layout.addWidget(self._progress)

        # ── Buttons ────────────────────────────────────────────
        btn_row = QHBoxLayout()

        self._btn_skip = QPushButton(tr("update.btn_skip"))
        self._btn_skip.clicked.connect(self.reject)
        btn_row.addWidget(self._btn_skip)

        btn_row.addStretch()

        self._btn_remind = QPushButton(tr("update.btn_remind"))
        self._btn_remind.clicked.connect(self.reject)
        btn_row.addWidget(self._btn_remind)

        self._btn_download = QPushButton(tr("update.btn_download"))
        self._btn_download.setStyleSheet(
            "QPushButton { background-color: #2196F3; color: white; "
            "padding: 10px 20px; font-size: 14px; border-radius: 4px; font-weight: bold; }"
            "QPushButton:hover { background-color: #1976D2; }"
        )
        self._btn_download.clicked.connect(self._on_download)
        btn_row.addWidget(self._btn_download)

        layout.addLayout(btn_row)

    # ── Download flow ──────────────────────────────────────────

    def _on_download(self):
        """Start downloading the new installer."""
        # Pick default save path
        ext = os.path.splitext(self._info.download_name)[1] or ".exe"
        default_dir = os.path.expanduser("~/Downloads")
        if not os.path.isdir(default_dir):
            default_dir = os.path.expanduser("~")
        save_path = os.path.join(default_dir, self._info.download_name)

        # Let user choose where to save
        if sys.platform == "win32":
            filter_str = f"Installer (*{ext});;All Files (*)"
        else:
            filter_str = f"Disk Image (*{ext});;All Files (*)"
        path, _ = QFileDialog.getSaveFileName(self, tr("update.btn_download"), save_path, filter_str)
        if not path:
            return

        # Switch to download mode
        self._btn_download.setEnabled(False)
        self._btn_download.setText(tr("update.downloading", percent="0"))
        self._btn_skip.setEnabled(False)
        self._btn_remind.setEnabled(False)
        self._progress.setVisible(True)
        self._progress.setValue(0)

        # Start background download
        self._thread = QThread(self)
        self._worker = _DownloadWorker(self._info.download_url, path)
        self._worker.moveToThread(self._thread)

        self._thread.started.connect(self._worker.run)
        self._worker.progress.connect(self._on_progress)
        self._worker.finished.connect(self._on_download_done)
        self._worker.error.connect(self._on_download_error)

        self._thread.start()

    def _on_progress(self, pct: int):
        self._progress.setValue(pct)
        self._btn_download.setText(tr("update.downloading", percent=str(pct)))

    def _on_download_done(self, path: str):
        self._cleanup_thread()
        self._downloaded_path = path

        # Ask: open installer now?
        reply = QMessageBox.question(
            self, tr("update.title"),
            tr("update.download_complete", path=path),
            QMessageBox.Yes | QMessageBox.No, QMessageBox.Yes,
        )
        if reply == QMessageBox.Yes:
            self._launch_installer(path)
        self.accept()

    def _on_download_error(self, msg: str):
        self._cleanup_thread()
        QMessageBox.critical(self, tr("update.title"), msg)
        self.reject()

    def _launch_installer(self, path: str):
        """Open the installer and quit the app."""
        if sys.platform == "win32":
            os.startfile(path)
        elif sys.platform == "darwin":
            import subprocess
            subprocess.Popen(["open", path])
        else:
            webbrowser.open(path)
        QApplication.quit()

    def _cleanup_thread(self):
        if self._worker:
            self._worker.cancel()
        if self._thread:
            self._thread.quit()
            self._thread.wait(3000)
            self._thread = None
            self._worker = None


# ── Convenience helpers ───────────────────────────────────────────

def show_update_dialog(info: UpdateInfo, parent=None):
    """Blocking convenience: show the update dialog and return when closed."""
    dlg = UpdateDialog(info, parent)
    dlg.exec_()


def check_and_notify(parent=None):
    """Check for updates in background; show dialog if one is available.

    Safe to call from the main thread — network runs synchronously but
    is fast enough (< 1 s for GitHub API).  For startup use, consider
    running in a QThread if latency is a concern.
    """
    from src.core.updater import check_for_updates

    try:
        info = check_for_updates()
    except Exception as e:
        # Don't bother the user on startup — just log and move on.
        # If called from menu, the caller should handle the error.
        return None

    if info is None:
        return None  # Up to date

    show_update_dialog(info, parent)
    return info
