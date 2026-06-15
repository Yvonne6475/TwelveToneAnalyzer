"""Shared ScoreOpener: QMenu with File/URL/Corpus options for opening scores.

All heavy operations (I/O, download, corpus.parse) run on a QThread worker,
keeping the UI responsive.
"""
from __future__ import annotations

from PyQt5.QtWidgets import (
    QMenu, QAction, QFileDialog, QMessageBox,
    QDialog, QVBoxLayout, QLabel, QLineEdit, QDialogButtonBox,
    QApplication,
)
from PyQt5.QtCore import Qt, QThread, pyqtSignal, QObject

from src.core.file_manager import load_local_file, download_from_url, parse_corpus
from src.utils.i18n import tr


class _LoadWorker(QObject):
    """Loads a score file/URL/corpus in a background thread."""
    finished = pyqtSignal(object, str)
    error = pyqtSignal(str)

    def __init__(self):
        super().__init__()
        self._cancelled = False

    def cancel(self):
        self._cancelled = True

    def do_load_file(self, path: str):
        try:
            if self._cancelled:
                return
            score = load_local_file(path)
            if not self._cancelled:
                self.finished.emit(score, path)
        except Exception as e:
            if not self._cancelled:
                self.error.emit(str(e))

    def do_load_url(self, url: str):
        try:
            if self._cancelled:
                return
            from src.utils.config import get_temp_dir
            file_path, score = download_from_url(url, get_temp_dir())
            if not self._cancelled:
                self.finished.emit(score, file_path)
        except Exception as e:
            if not self._cancelled:
                self.error.emit(str(e))

    def do_load_corpus(self, name: str):
        try:
            if self._cancelled:
                return
            _, score = parse_corpus(name)
            if not self._cancelled:
                self.finished.emit(score, name)
        except Exception as e:
            if not self._cancelled:
                self.error.emit(str(e))


# Track active loader thread so rapid reloads don't orphan workers.
_active_worker: _LoadWorker | None = None
_active_thread: QThread | None = None


def _cleanup_active_loader():
    """Cancel and clean up the currently running loader (if any)."""
    global _active_worker, _active_thread
    if _active_worker is not None:
        _active_worker.cancel()
    if _active_thread is not None:
        _active_thread.quit()
        if not _active_thread.wait(3000):
            _active_thread.terminate()
        _active_thread.deleteLater()
        _active_worker.deleteLater()
    _active_worker = None
    _active_thread = None


def load_score_async(parent, on_ready, task: str, *args):
    """Run a score-loading task in a background thread.

    Args:
        parent: QWidget parent (for dialogs and thread parent).
        on_ready: callable(score, path) — called on UI thread on success.
        task: 'file' (path), 'url' (url), or 'corpus' (name).
    """
    _spawn_worker(parent, on_ready, task, *args)


def _spawn_worker(parent, on_ready, task: str, *args):
    global _active_worker, _active_thread

    # Cancel any previous loader still running
    _cleanup_active_loader()

    QApplication.setOverrideCursor(Qt.WaitCursor)

    thread = QThread(parent)
    worker = _LoadWorker()
    worker.moveToThread(thread)

    _active_thread = thread
    _active_worker = worker

    def _on_finished(score, path):
        QApplication.restoreOverrideCursor()
        thread.quit()
        _cleanup_active_loader()
        on_ready(score, path)

    def _on_error(msg):
        QApplication.restoreOverrideCursor()
        thread.quit()
        _cleanup_active_loader()
        QMessageBox.critical(parent, tr("dialog.load_failed"), msg)

    worker.finished.connect(_on_finished)
    worker.error.connect(_on_error)
    thread.started.connect(
        lambda: getattr(worker, f"do_load_{task}")(*args)
    )
    thread.finished.connect(lambda: worker.deleteLater())
    thread.finished.connect(lambda: thread.deleteLater())
    thread.start()


def setup_open_menu(button, parent_widget, on_score_ready) -> QMenu:
    """Attach a 3-way popup menu (File / URL / Corpus) to a QPushButton."""
    menu = QMenu(button)

    act_file = QAction(tr("menu.file.open"), parent_widget)
    act_file.triggered.connect(lambda: _open_file(parent_widget, on_score_ready))
    menu.addAction(act_file)

    act_url = QAction(tr("menu.file.open_url"), parent_widget)
    act_url.triggered.connect(lambda: _open_url(parent_widget, on_score_ready))
    menu.addAction(act_url)

    act_corpus = QAction(tr("menu.file.open_corpus"), parent_widget)
    act_corpus.triggered.connect(lambda: _open_corpus(parent_widget, on_score_ready))
    menu.addAction(act_corpus)

    button.setMenu(menu)
    button.clicked.connect(button.showMenu)
    return menu


def _open_file(parent, on_ready):
    path, _ = QFileDialog.getOpenFileName(
        parent, tr("dialog.open_score"), "",
        tr("dialog.open_score_filter")
    )
    if not path:
        return
    _spawn_worker(parent, on_ready, "file", path)


CORPUS_LIBRARY_URL = "https://github.com/Yvonne6475/My-music-Corpus-Library"


def prompt_url_dialog(parent, title: str, label: str, default_text: str = "") -> str:
    """Show a reusable URL input dialog with a corpus library link.

    Args:
        parent: Parent widget.
        title: Dialog window title.
        label: Label text above the URL input.
        default_text: Pre-filled URL text.

    Returns:
        The entered URL (stripped), or empty string if cancelled.
    """
    import webbrowser
    from PyQt5.QtWidgets import QPushButton

    dlg = QDialog(parent)
    dlg.setWindowTitle(title)
    dlg.setMinimumWidth(700)
    dlg.setWindowFlags(dlg.windowFlags() & ~Qt.WindowContextHelpButtonHint)
    dlg_layout = QVBoxLayout(dlg)
    dlg_layout.addWidget(QLabel(label))
    url_edit = QLineEdit(default_text)
    url_edit.setPlaceholderText(tr("dialog.url_placeholder"))
    dlg_layout.addWidget(url_edit)
    link_btn = QPushButton(tr("dialog.corpus_library_link"))
    link_btn.setFlat(True)
    link_btn.setStyleSheet(
        "color: #4a9eff; text-decoration: underline; text-align: left; border: none; padding: 0;"
    )
    link_btn.setCursor(Qt.PointingHandCursor)
    link_btn.clicked.connect(lambda: webbrowser.open(CORPUS_LIBRARY_URL))
    dlg_layout.addWidget(link_btn)
    buttons = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
    buttons.accepted.connect(dlg.accept)
    buttons.rejected.connect(dlg.reject)
    dlg_layout.addWidget(buttons)
    if dlg.exec_() == QDialog.Accepted:
        return url_edit.text().strip()
    return ""


def _open_url(parent, on_ready):
    url = prompt_url_dialog(parent, tr("dialog.url_prompt"), tr("dialog.url_label"))
    if not url:
        return
    _spawn_worker(parent, on_ready, "url", url)


CORPUS_REFERENCE_URL = "https://music21.org/music21docs/about/referenceCorpus.html"


def _open_corpus(parent, on_ready):
    name = _prompt_corpus_name(parent)
    if not name:
        return
    _spawn_worker(parent, on_ready, "corpus", name)


def _prompt_corpus_name(parent) -> str:
    """Show a dialog with corpus name input + a 'Browse Reference' button.
    Returns the entered name, or empty string if cancelled.
    """
    import webbrowser
    from PyQt5.QtWidgets import QPushButton, QHBoxLayout

    dlg = QDialog(parent)
    dlg.setWindowTitle(tr("dialog.corpus_prompt"))
    dlg.setMinimumWidth(550)
    dlg.setWindowFlags(dlg.windowFlags() & ~Qt.WindowContextHelpButtonHint)
    dlg_layout = QVBoxLayout(dlg)

    dlg_layout.addWidget(QLabel(tr("dialog.corpus_label")))
    name_edit = QLineEdit()
    name_edit.setPlaceholderText("e.g. bach/bwv66.6")
    dlg_layout.addWidget(name_edit)

    btn_row = QHBoxLayout()
    btn_browse = QPushButton(tr("dialog.corpus_browse"))
    btn_browse.clicked.connect(lambda: webbrowser.open(CORPUS_REFERENCE_URL))
    btn_row.addWidget(btn_browse)
    btn_row.addStretch()
    dlg_layout.addLayout(btn_row)

    buttons = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
    buttons.accepted.connect(dlg.accept)
    buttons.rejected.connect(dlg.reject)
    dlg_layout.addWidget(buttons)

    if dlg.exec_() != QDialog.Accepted:
        return ""
    return name_edit.text().strip()
