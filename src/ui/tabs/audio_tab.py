"""Audio analysis tab: spectrogram, chromagram, MFCC, tonnetz, tempogram, structural segmentation."""

import os
import numpy as np
from pathlib import Path

from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QGroupBox, QLabel,
    QComboBox, QSpinBox, QPushButton, QFileDialog, QMessageBox,
    QScrollArea, QMenu, QAction, QDialog, QLineEdit, QDialogButtonBox,
    QApplication, QProgressBar,
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
from src.utils.config import temp_default_path


class _AudioLoadWorker(QObject):
    """Background worker: loads audio with chunked reading for real progress."""
    finished = pyqtSignal(object, int)  # (y, sr)
    progress = pyqtSignal(int)          # 0–100
    error = pyqtSignal(str)

    def do_load(self, path):
        import soundfile as sf
        import numpy as np
        try:
            info = sf.info(path)
            total_frames = info.frames
            sr = info.samplerate
            chunk_size = max(4096, total_frames // 200)  # ~200 updates
            y_parts = []
            frames_read = 0
            with sf.SoundFile(path) as f:
                while frames_read < total_frames:
                    chunk = f.read(chunk_size, dtype='float32', always_2d=False)
                    if len(chunk) == 0:
                        break
                    y_parts.append(chunk)
                    frames_read += len(chunk)
                    pct = int(frames_read / total_frames * 100)
                    self.progress.emit(pct)
            y = np.concatenate(y_parts)
            # convert stereo → mono
            if y.ndim == 2:
                y = y.mean(axis=1)
            self.finished.emit(y, sr)
        except Exception as e:
            self.error.emit(str(e))


class _AnalysisWorker(QObject):
    """Background worker: computes audio features without blocking UI."""
    finished = pyqtSignal(object)  # result dict
    error = pyqtSignal(str)

    def do_analyze(self, y, sr, choice, n_seg):
        import numpy as np
        try:
            result = {"choice": choice, "n_seg": n_seg}
            if choice == 0:  # waveform – nothing heavy to compute
                total = len(y) / sr
                result["seg_times"] = np.linspace(0, total, n_seg + 1)
            elif choice == 1:  # spectrogram
                D = compute_spectrogram(y, sr)
                result["D"] = D
                result["vmin"] = float(D.min())
                result["vmax"] = float(D.max())
                bounds = np.linspace(0, D.shape[1], n_seg + 1).astype(int)
                result["bounds"] = bounds
                result["bound_times"] = (bounds * 1024 / sr).tolist()
                result["hop_length"] = 1024
            elif choice == 2:  # chromagram
                chroma = compute_chromagram(y, sr)
                bounds = segment_structure(chroma, n_seg, axis=1)
                result["chroma"] = chroma
                result["bounds"] = bounds
                result["bound_times"] = frames_to_time(bounds, sr).tolist()
            elif choice == 3:  # MFCC
                mfccs = compute_mfcc(y, sr)
                bounds = segment_structure(mfccs, n_seg, axis=1)
                result["mfccs"] = mfccs
                result["bounds"] = bounds
                result["bound_times"] = frames_to_time(bounds, sr, hop_length=256).tolist()
            elif choice == 4:  # tonnetz
                tonnetz = compute_tonnetz(y, sr)
                bounds = segment_structure(tonnetz, n_seg, axis=1)
                result["tonnetz"] = tonnetz
                result["bounds"] = bounds
                result["bound_times"] = frames_to_time(bounds, sr).tolist()
            elif choice == 5:  # tempogram
                tempo = compute_tempogram(y, sr)
                bounds = segment_structure(tempo, n_seg, axis=1)
                result["tempo"] = tempo
                result["bounds"] = bounds
                result["bound_times"] = frames_to_time(bounds, sr, hop_length=1024).tolist()
            self.finished.emit(result)
        except Exception as e:
            self.error.emit(str(e))


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

        self._progress = QProgressBar()
        self._progress.setMinimum(0)
        self._progress.setMaximum(0)  # indeterminate / marquee mode
        self._progress.setVisible(False)
        self._progress.setMaximumHeight(20)
        self._progress.setFormat("  %p%")
        self._progress.setStyleSheet(
            "QProgressBar { border: 2px solid #7b68ee; border-radius: 4px; "
            "background: #f0f0f0; text-align: center; font-weight: bold; }"
            "QProgressBar::chunk { background-color: #7b68ee; }"
        )
        layout.addWidget(self._progress)

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
        self._scroll_area.setStyleSheet("QScrollArea { background-color: #fefdfb; border: none; }")
        layout.addWidget(self._scroll_area, 1)

    def _show_progress(self, determinate=True):
        self._progress.setVisible(True)
        if determinate:
            self._progress.setMinimum(0)
            self._progress.setMaximum(100)
            self._progress.setValue(0)
        else:
            self._progress.setMinimum(0)
            self._progress.setMaximum(0)  # indeterminate
        self._btn_analyze.setEnabled(False)
        self._btn_load.setEnabled(False)
        self._analysis_combo.setEnabled(False)
        self._spin_segments.setEnabled(False)
        QApplication.processEvents()

    def _hide_progress(self):
        self._progress.setVisible(False)
        self._btn_load.setEnabled(True)
        self._analysis_combo.setEnabled(True)
        self._spin_segments.setEnabled(True)
        if self._y is not None:
            self._btn_analyze.setEnabled(True)

    def on_score_loaded(self, score=None, path=None):
        """Clear old audio analysis when a new score is loaded."""
        self._audio_path = ""
        self._y = None
        self._sr = None
        self._lbl_file.setText(tr("audio.no_file"))
        self._btn_analyze.setEnabled(False)
        self._btn_save_plot.setEnabled(False)
        self._canvas.fig.clear()
        self._canvas.draw_idle()

    def on_audio_loaded(self, path: str):
        self._audio_path = path
        self._lbl_file.setText(tr("audio.loading", name=Path(path).name))
        # Clear old analysis plots — user must re-analyze
        self._btn_analyze.setEnabled(False)
        self._btn_save_plot.setEnabled(False)
        self._canvas.fig.clear()
        self._canvas.draw_idle()
        self._show_progress(determinate=True)

        thread = QThread(self)
        worker = _AudioLoadWorker()
        worker.moveToThread(thread)

        def _on_progress(pct):
            self._progress.setValue(pct)

        def _on_finished(y, sr):
            self._y = y
            self._sr = sr
            dur = len(y) / sr
            self._lbl_file.setText(
                tr("audio.loaded", name=Path(path).name, sr=sr, dur=dur)
            )
            self._btn_analyze.setEnabled(True)
            self._hide_progress()
            thread.quit()

        def _on_error(msg):
            self._hide_progress()
            thread.quit()
            QMessageBox.critical(self, tr("audio.load_failed"), msg)

        worker.progress.connect(_on_progress)
        worker.finished.connect(_on_finished)
        worker.error.connect(_on_error)
        thread.started.connect(lambda: worker.do_load(path))
        thread.finished.connect(lambda: worker.deleteLater())
        thread.finished.connect(lambda: thread.deleteLater())
        thread.start()

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
        url_edit.setPlaceholderText(tr("dialog.url_placeholder"))
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

        if choice == 0:
            # waveform: fast enough to run inline with progress bar
            self._show_progress(determinate=False)
            try:
                self._plot_waveform(n_seg)
                self._btn_save_plot.setEnabled(True)
            except Exception as e:
                QMessageBox.warning(self, tr("audio.analysis_error"), str(e))
            finally:
                self._hide_progress()
            return

        # choices 1–5: heavy computation in background thread
        self._show_progress(determinate=False)
        thread = QThread(self)
        worker = _AnalysisWorker()
        worker.moveToThread(thread)

        def _on_finished(result):
            try:
                n = result["n_seg"]
                if result["choice"] == 1:
                    self._plot_spectrogram_from(result)
                elif result["choice"] == 2:
                    self._plot_chromagram_from(result)
                elif result["choice"] == 3:
                    self._plot_mfcc_from(result)
                elif result["choice"] == 4:
                    self._plot_tonnetz_from(result)
                elif result["choice"] == 5:
                    self._plot_tempogram_from(result)
                self._btn_save_plot.setEnabled(True)
            except Exception as e:
                QMessageBox.warning(self, tr("audio.analysis_error"), str(e))
            finally:
                self._hide_progress()
                thread.quit()

        def _on_error(msg):
            self._hide_progress()
            thread.quit()
            QMessageBox.warning(self, tr("audio.analysis_error"), msg)

        worker.finished.connect(_on_finished)
        worker.error.connect(_on_error)
        thread.started.connect(lambda: worker.do_analyze(self._y, self._sr, choice, n_seg))
        thread.finished.connect(lambda: worker.deleteLater())
        thread.finished.connect(lambda: thread.deleteLater())
        thread.start()

    def _time_segments(self, n_seg):
        """Split full duration into equal-time segment boundaries."""
        total = len(self._y) / self._sr
        return np.linspace(0, total, n_seg + 1)

    # ── plotting-from-worker helpers (main-thread matplotlib only) ──

    def _plot_spectrogram_from(self, r):
        import librosa.display
        D = r["D"]
        bounds = r["bounds"]
        bound_times = r["bound_times"]
        n_seg = r["n_seg"]
        self._canvas.fig.clear()
        self._canvas.set_size_inches(18, 24)
        vmin, vmax = r["vmin"], r["vmax"]
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

    def _plot_chromagram_from(self, r):
        import librosa.display
        chroma = r["chroma"]
        bounds = r["bounds"]
        bound_times = r["bound_times"]
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

    def _plot_mfcc_from(self, r):
        import librosa.display
        mfccs = r["mfccs"]
        bounds = r["bounds"]
        bound_times = r["bound_times"]
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

    def _plot_tonnetz_from(self, r):
        import librosa.display
        tonnetz = r["tonnetz"]
        bounds = r["bounds"]
        bound_times = r["bound_times"]
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

    def _plot_tempogram_from(self, r):
        import librosa.display
        tempo = r["tempo"]
        bounds = r["bounds"]
        bound_times = r["bound_times"]
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

    # ── original plot methods (used inline for waveform; kept for fallback) ──

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
            self, tr("audio.save_png"), temp_default_path("audio_analysis.png"),
            "PNG (*.png);;All Files (*)"
        )
        if path:
            self._canvas.fig.savefig(path, dpi=150, bbox_inches='tight')
            QMessageBox.information(self, tr("audio.save_done"),
                                    tr("dialog.saved_to", path=path))
