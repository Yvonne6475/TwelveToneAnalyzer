"""Audio analysis tab: spectrogram, chromagram, MFCC, tonnetz, tempogram, structural segmentation."""

import os
import numpy as np
from pathlib import Path

from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QGroupBox, QLabel,
    QComboBox, QSpinBox, QPushButton, QFileDialog, QMessageBox,
    QScrollArea, QMenu, QAction, QDialog, QLineEdit, QDialogButtonBox,
    QApplication,
)
from PyQt5.QtCore import Qt, QThread, pyqtSignal, QObject

import matplotlib.pyplot as plt

from src.ui.widgets.plot_canvas import PlotCanvas
from src.core.audio_analyzer import (
    load_audio, compute_spectrogram, compute_chromagram,
    compute_mfcc, compute_tonnetz, compute_tempogram,
    segment_structure, frames_to_time,
)
from src.utils.i18n import tr, tr_list


class AudioTab(QWidget):
    def __init__(self, main_window=None):
        super().__init__()
        self._main_window = main_window
        self._audio_path = ""
        self._y = None
        self._sr = None
        self._setup_ui()

    def _setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(6, 6, 6, 6)

        load_group = QGroupBox(tr("audio.file_group"))
        load_layout = QHBoxLayout(load_group)
        self._lbl_file = QLabel(tr("audio.no_file"))
        load_layout.addWidget(self._lbl_file)
        self._btn_load = QPushButton(tr("audio.btn_load"))
        load_menu = QMenu(self._btn_load)
        load_menu.addAction(tr("menu.file.open_audio")).triggered.connect(self._on_load_audio)
        load_menu.addAction(tr("menu.file.open_url")).triggered.connect(self._on_load_audio_url)
        self._btn_load.setMenu(load_menu)
        self._btn_load.clicked.connect(self._btn_load.showMenu)
        load_layout.addWidget(self._btn_load)
        load_layout.addStretch()
        layout.addWidget(load_group)

        ctrl_group = QGroupBox(tr("audio.ctrl_group"))
        ctrl_layout = QHBoxLayout(ctrl_group)

        ctrl_layout.addWidget(QLabel(tr("audio.type_label")))
        self._analysis_combo = QComboBox()
        self._analysis_combo.addItems(tr_list("audio.analysis_types"))
        ctrl_layout.addWidget(self._analysis_combo)

        ctrl_layout.addWidget(QLabel(tr("audio.segments_label")))
        self._spin_segments = QSpinBox()
        self._spin_segments.setMinimum(2)
        self._spin_segments.setMaximum(20)
        self._spin_segments.setValue(8)
        ctrl_layout.addWidget(self._spin_segments)

        ctrl_layout.addStretch()

        self._btn_analyze = QPushButton(tr("audio.btn_analyze"))
        self._btn_analyze.setProperty("accent", "purple")
        self._btn_analyze.setEnabled(False)
        self._btn_analyze.clicked.connect(self._on_analyze)
        ctrl_layout.addWidget(self._btn_analyze)

        layout.addWidget(ctrl_group)

        btn_row = QHBoxLayout()
        self._btn_save_plot = QPushButton(tr("audio.btn_save_plot"))
        self._btn_save_plot.setEnabled(False)
        self._btn_save_plot.clicked.connect(self._on_save_plot)
        btn_row.addWidget(self._btn_save_plot)
        btn_row.addStretch()
        layout.addLayout(btn_row)

        self._canvas = PlotCanvas(self)
        self._scroll_area = QScrollArea()
        self._scroll_area.setWidgetResizable(False)
        self._scroll_area.setWidget(self._canvas)
        layout.addWidget(self._scroll_area, 1)

    def on_audio_loaded(self, path: str):
        self._audio_path = path
        self._lbl_file.setText(tr("audio.no_file"))
        try:
            self._y, self._sr = load_audio(path)
            dur = len(self._y) / self._sr
            self._lbl_file.setText(
                tr("audio.loaded", name=Path(path).name, sr=self._sr, dur=dur)
            )
            self._btn_analyze.setEnabled(True)
        except Exception as e:
            QMessageBox.critical(self, tr("audio.load_failed"), str(e))

    def _on_load_audio(self):
        path, _ = QFileDialog.getOpenFileName(
            self, tr("dialog.open_audio"), "",
            tr("dialog.open_audio_filter")
        )
        if path:
            self.on_audio_loaded(path)

    def _on_load_audio_url(self):
        dlg = QDialog(self)
        dlg.setWindowTitle(tr("dialog.url_prompt"))
        dlg.setMinimumWidth(700)
        dlg.setWindowFlags(dlg.windowFlags() & ~Qt.WindowContextHelpButtonHint)
        dlg_layout = QVBoxLayout(dlg)
        dlg_layout.addWidget(QLabel(tr("dialog.url_label")))
        url_edit = QLineEdit()
        dlg_layout.addWidget(url_edit)
        buttons = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        buttons.accepted.connect(dlg.accept)
        buttons.rejected.connect(dlg.reject)
        dlg_layout.addWidget(buttons)
        if dlg.exec_() != QDialog.Accepted:
            return
        url = url_edit.text().strip()
        if not url:
            return
        self._start_audio_download(url)

    def _start_audio_download(self, url: str):
        """Download audio from URL in a background thread."""
        import requests, tempfile
        from urllib.parse import urlparse

        class _AudioDLWorker(QObject):
            finished = pyqtSignal(str)
            error = pyqtSignal(str)

            def do_download(self, u):
                try:
                    response = requests.get(u, timeout=30)
                    response.raise_for_status()
                    ext = Path(urlparse(u).path).suffix or ".wav"
                    tmp = tempfile.NamedTemporaryFile(suffix=ext, delete=False)
                    tmp.write(response.content)
                    tmp.close()
                    self.finished.emit(tmp.name)
                except Exception as e:
                    self.error.emit(str(e))

        QApplication.setOverrideCursor(Qt.WaitCursor)
        thread = QThread(self)
        worker = _AudioDLWorker()
        worker.moveToThread(thread)

        def _on_finished(path):
            QApplication.restoreOverrideCursor()
            thread.quit()
            self.on_audio_loaded(path)

        def _on_error(msg):
            QApplication.restoreOverrideCursor()
            thread.quit()
            QMessageBox.critical(self, tr("dialog.download_failed"), msg)

        worker.finished.connect(_on_finished)
        worker.error.connect(_on_error)
        thread.started.connect(lambda: worker.do_download(url))
        thread.finished.connect(lambda: worker.deleteLater())
        thread.finished.connect(lambda: thread.deleteLater())
        thread.start()

    def _on_analyze(self):
        if self._y is None:
            return
        choice = self._analysis_combo.currentIndex()
        n_seg = self._spin_segments.value()

        try:
            if choice == 0:
                self._plot_waveform(n_seg)
            elif choice == 1:
                self._plot_spectrogram(n_seg)
            elif choice == 2:
                self._plot_chromagram(n_seg)
            elif choice == 3:
                self._plot_mfcc(n_seg)
            elif choice == 4:
                self._plot_tonnetz(n_seg)
            elif choice == 5:
                self._plot_tempogram(n_seg)
            self._btn_save_plot.setEnabled(True)
        except Exception as e:
            QMessageBox.warning(self, tr("audio.analysis_error"), str(e))

    def _time_segments(self, n_seg):
        """Split full duration into equal-time segment boundaries."""
        total = len(self._y) / self._sr
        return np.linspace(0, total, n_seg + 1)

    def _plot_waveform(self, n_seg):
        import librosa.display
        seg_times = self._time_segments(n_seg)
        self._canvas.fig.clear()
        self._canvas.set_size_inches(18, 24)
        for i in range(n_seg):
            ax = self._canvas.fig.add_subplot(n_seg, 1, i + 1)
            t0, t1 = seg_times[i], seg_times[i+1]
            n0, n1 = int(t0 * self._sr), int(t1 * self._sr)
            librosa.display.waveshow(y=self._y[n0:n1], sr=self._sr, ax=ax,
                                     offset=t0)
            ax.set_title(f"Seg {i+1}: {t0:.1f}s – {t1:.1f}s")
            ax.set_xlabel("Time (s)")
        self._canvas.tight_layout()
        self._canvas.draw()

    def _frame_segments(self, n_frames, n_seg, hop_length, sr):
        """Compute segment boundaries from feature frames."""
        bounds = np.linspace(0, n_frames, n_seg + 1).astype(int)
        bound_times = bounds * hop_length / sr
        return bounds, bound_times

    def _plot_spectrogram(self, n_seg):
        import librosa.display
        D = compute_spectrogram(self._y, self._sr)
        bounds, bound_times = self._frame_segments(D.shape[1], n_seg, 1024, self._sr)
        self._canvas.fig.clear()
        self._canvas.set_size_inches(18, 24)
        vmin, vmax = D.min(), D.max()
        for i in range(n_seg):
            ax = self._canvas.fig.add_subplot(n_seg, 1, i + 1)
            seg = D[:, bounds[i]:bounds[i+1]]
            t0 = bound_times[i]
            img = librosa.display.specshow(seg, y_axis='log', sr=self._sr, hop_length=1024,
                                           x_axis='time', cmap='jet', ax=ax,
                                           vmin=vmin, vmax=vmax,
                                           x_coords=np.linspace(t0, bound_times[i+1], seg.shape[1]))
            ax.set_title(f"Seg {i+1}: {t0:.1f}s – {bound_times[i+1]:.1f}s")
            self._canvas.fig.colorbar(img, ax=ax, format='%+2.0f dB')
        self._canvas.tight_layout()
        self._canvas.draw()

    def _plot_chromagram(self, n_seg):
        import librosa.display
        chroma = compute_chromagram(self._y, self._sr)
        bounds = segment_structure(chroma, n_seg, axis=1)
        bound_times = frames_to_time(bounds, self._sr)

        n = len(bounds) - 1
        self._canvas.fig.clear()
        self._canvas.set_size_inches(18, 24)
        for i in range(n):
            ax = self._canvas.fig.add_subplot(n, 1, i + 1)
            seg = chroma[:, bounds[i]:bounds[i+1]]
            t0 = bound_times[i]
            librosa.display.specshow(seg, y_axis='chroma', x_axis='time',
                                     sr=self._sr, hop_length=512, ax=ax,
                                     x_coords=np.linspace(t0, bound_times[i+1], seg.shape[1]))
            ax.set_title(f"Seg {i+1}: {t0:.1f}s – {bound_times[i+1]:.1f}s")
            ax.set_yticks(np.arange(12))
            ax.set_yticklabels(['C','C#','D','D#','E','F','F#','G','G#','A','A#','B'])
        self._canvas.tight_layout()
        self._canvas.draw()

    def _plot_mfcc(self, n_seg):
        import librosa.display
        mfccs = compute_mfcc(self._y, self._sr)
        bounds = segment_structure(mfccs, n_seg, axis=1)
        bound_times = frames_to_time(bounds, self._sr, hop_length=256)

        n = len(bounds) - 1
        self._canvas.fig.clear()
        self._canvas.set_size_inches(18, 24)
        for i in range(n):
            ax = self._canvas.fig.add_subplot(n, 1, i + 1)
            seg = mfccs[:, bounds[i]:bounds[i+1]]
            t0 = bound_times[i]
            librosa.display.specshow(seg, x_axis='time', sr=self._sr,
                                     hop_length=256, ax=ax,
                                     x_coords=np.linspace(t0, bound_times[i+1], seg.shape[1]))
            ax.set_title(f"Seg {i+1}: {t0:.1f}s – {bound_times[i+1]:.1f}s")
        self._canvas.tight_layout()
        self._canvas.draw()

    def _plot_tonnetz(self, n_seg):
        import librosa.display
        tonnetz = compute_tonnetz(self._y, self._sr)
        bounds = segment_structure(tonnetz, n_seg, axis=1)
        bound_times = frames_to_time(bounds, self._sr)

        n = len(bounds) - 1
        self._canvas.fig.clear()
        self._canvas.set_size_inches(18, 24)
        for i in range(n):
            ax = self._canvas.fig.add_subplot(n, 1, i + 1)
            seg = tonnetz[:, bounds[i]:bounds[i+1]]
            t0 = bound_times[i]
            librosa.display.specshow(seg, y_axis='tonnetz', x_axis='time',
                                     sr=self._sr, ax=ax, cmap='Accent',
                                     x_coords=np.linspace(t0, bound_times[i+1], seg.shape[1]))
            ax.set_title(f"Seg {i+1}: {t0:.1f}s – {bound_times[i+1]:.1f}s")
        self._canvas.tight_layout()
        self._canvas.draw()

    def _plot_tempogram(self, n_seg):
        import librosa.display
        tempo = compute_tempogram(self._y, self._sr)
        bounds = segment_structure(tempo, n_seg, axis=1)
        bound_times = frames_to_time(bounds, self._sr, hop_length=1024)

        n = len(bounds) - 1
        self._canvas.fig.clear()
        self._canvas.set_size_inches(18, 24)
        for i in range(n):
            ax = self._canvas.fig.add_subplot(n, 1, i + 1)
            seg = tempo[:, bounds[i]:bounds[i+1]]
            t0 = bound_times[i]
            librosa.display.specshow(seg, y_axis='tempo', x_axis='time',
                                     sr=self._sr, hop_length=1024, ax=ax, cmap='magma',
                                     x_coords=np.linspace(t0, bound_times[i+1], seg.shape[1]))
            ax.set_title(f"Seg {i+1}: {t0:.1f}s – {bound_times[i+1]:.1f}s")
        self._canvas.tight_layout()
        self._canvas.draw()

    def _on_save_plot(self):
        path, _ = QFileDialog.getSaveFileName(
            self, tr("audio.save_png"), "audio_analysis.png",
            "PNG (*.png);;All Files (*)"
        )
        if path:
            self._canvas.fig.savefig(path, dpi=150, bbox_inches='tight')
            QMessageBox.information(self, tr("audio.save_done"),
                                    tr("dialog.saved_to", path=path))
