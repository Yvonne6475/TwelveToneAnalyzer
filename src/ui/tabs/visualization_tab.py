"""Visualization tab: generate music21 plots with interactive controls."""

from PyQt5.QtWidgets import (
    QWidget, QHBoxLayout, QVBoxLayout, QGroupBox, QLabel,
    QComboBox, QSpinBox, QPushButton, QMessageBox, QFileDialog,
)
from PyQt5.QtCore import Qt

import matplotlib.pyplot as plt

from src.core.score_analyzer import get_measure_range
from src.ui.widgets.score_opener import setup_open_menu
from src.utils.i18n import tr, tr_list
from src.utils.config import temp_default_path


class VisualizationTab(QWidget):
    def __init__(self, main_window=None):
        super().__init__()
        self._main_window = main_window
        self._score = None
        self._midi_score = None
        self._max_measure = 272
        self._current_fig = None
        self._setup_ui()

    def _setup_ui(self):
        main_layout = QHBoxLayout(self)
        main_layout.setContentsMargins(6, 6, 6, 6)

        left = QWidget()
        left_layout = QVBoxLayout(left)
        left_layout.setContentsMargins(0, 0, 0, 0)

        self._btn_open = QPushButton(tr("tab.open_score"))
        setup_open_menu(self._btn_open, self, lambda score, path: self._main_window.set_score(score, path))
        left_layout.addWidget(self._btn_open)

        self._info_label = QLabel("")
        self._info_label.setStyleSheet("color: #888; padding: 4px 0;")
        left_layout.addWidget(self._info_label)

        part_group = QGroupBox(tr("viz.part_group"))
        part_layout = QVBoxLayout(part_group)
        self._part_combo = QComboBox()
        self._part_combo.setEnabled(False)
        part_layout.addWidget(self._part_combo)
        left_layout.addWidget(part_group)

        measure_group = QGroupBox(tr("viz.measure_group"))
        meas_layout = QVBoxLayout(measure_group)
        meas_layout.addWidget(QLabel(tr("viz.start_measure")))
        self._spin_start = QSpinBox()
        self._spin_start.setMinimum(1)
        self._spin_start.setMaximum(999)
        self._spin_start.setValue(1)
        meas_layout.addWidget(self._spin_start)
        meas_layout.addWidget(QLabel(tr("viz.end_measure")))
        self._spin_end = QSpinBox()
        self._spin_end.setMinimum(1)
        self._spin_end.setMaximum(999)
        self._spin_end.setValue(20)
        meas_layout.addWidget(self._spin_end)
        left_layout.addWidget(measure_group)

        plot_group = QGroupBox(tr("viz.plot_type"))
        plot_layout = QVBoxLayout(plot_group)
        self._plot_combo = QComboBox()
        self._plot_combo.addItems(tr_list("viz.plot_types"))
        plot_layout.addWidget(self._plot_combo)
        left_layout.addWidget(plot_group)

        self._btn_generate = QPushButton(tr("viz.btn_generate"))
        self._btn_generate.setProperty("accent", "green")
        self._btn_generate.setEnabled(False)
        self._btn_generate.clicked.connect(self._on_generate)
        left_layout.addWidget(self._btn_generate)

        self._btn_save = QPushButton(tr("viz.btn_save_png"))
        self._btn_save.setEnabled(False)
        self._btn_save.clicked.connect(self._on_save_png)
        left_layout.addWidget(self._btn_save)

        left_layout.addStretch()
        main_layout.addWidget(left, 1)

        right = QLabel(tr("viz.plot_placeholder"))
        right.setAlignment(Qt.AlignCenter)
        right.setStyleSheet("color: #888; font-size: 18px;")
        main_layout.addWidget(right, 3)

    def on_score_loaded(self, score, path: str):
        self._score = score
        self._max_measure = get_measure_range(score)[1]
        self._spin_end.setMaximum(self._max_measure)
        self._spin_end.setValue(min(20, self._max_measure))

        num_parts = len(score.parts) if hasattr(score, 'parts') else 1
        self._info_label.setText(tr("viz.score_info", parts=num_parts, measures=self._max_measure))

        self._part_combo.clear()
        self._part_combo.addItem(tr("viz.all_parts"), -1)
        try:
            for i, part in enumerate(score.parts):
                name = part.partName if part.partName else f"Part {i+1}"
                self._part_combo.addItem(f"{i}: {name}", i)
        except (AttributeError, IndexError):
            self._part_combo.addItem("0: Single Part", 0)

        self._part_combo.setEnabled(True)
        self._btn_generate.setEnabled(True)

        mw = self._main_window
        if mw and mw.midi_score:
            self._midi_score = mw.midi_score

    def on_language_changed(self):
        pass

    @staticmethod
    def _extract_notes(stream, part_idx: int):
        """Extract (pitchClass, quarterLength, measureNumber) from a stream/part."""
        import music21
        if part_idx >= 0 and hasattr(stream, 'parts'):
            try:
                s = stream.parts[part_idx].measures(1, None)
            except (IndexError, AttributeError):
                s = stream
        else:
            s = stream
        notes = []
        for el in s.recurse():
            if isinstance(el, (music21.note.Note, music21.chord.Chord)):
                m = el.getContextByClass('Measure')
                mn = m.number if m else 0
                if isinstance(el, music21.note.Note):
                    notes.append((el.pitch.pitchClass, el.quarterLength, mn))
                else:
                    for p in el.pitches:
                        notes.append((p.pitchClass, el.quarterLength, mn))
        return notes

    def _on_generate(self):
        if not self._score:
            return
        part_idx = self._part_combo.currentData()
        start = self._spin_start.value()
        end = self._spin_end.value()
        plot_idx = self._plot_combo.currentIndex()

        if start > end:
            QMessageBox.warning(self, tr("viz.range_error"), tr("viz.range_error_msg"))
            return

        try:
            plt.close('all')
            self._generate_plot(plot_idx, part_idx, start, end)
            self._current_fig = plt.gcf()
            self._current_plot_idx = plot_idx
            self._btn_save.setEnabled(True)
        except Exception as e:
            QMessageBox.warning(self, tr("viz.plot_error"), str(e))

    def _generate_plot(self, plot_type: int, part_idx: int, start: int, end: int):
        import sys
        from music21 import graph

        excerpt = self._score.measures(start, end)

        # On Windows, music21's plot() internal display doesn't work in frozen
        # apps.  Use pure matplotlib with plt.show() — same pattern as the
        # matrix heatmap widget which is confirmed working on Windows.
        if sys.platform == 'win32':
            return self._generate_plot_win32(plot_type, part_idx, start, end)

        # ── macOS: music21 native plot() ─────────────────────────────
        if plot_type == 0:
            excerpt.plot()
        elif plot_type == 1:
            excerpt.plot('histogram', 'pitchClass')
        elif plot_type == 2:
            p = graph.plot.ScatterWeightedPitchClassQuarterLength(excerpt)
            p.run()
        elif plot_type == 3:
            excerpt.plot('scatter', 'measure', 'pitchClass')
        elif plot_type == 4:
            src = self._midi_score if self._midi_score else self._score
            src.measures(start, end).plot('horizontalbarweighted')
        elif plot_type == 5:
            src = self._midi_score if self._midi_score else self._score
            plot_3d = src.measures(start, end).plot('3dbars', show=False)
            plot_3d.figure.set_size_inches(16, 16)
            plt.tight_layout()
            self._show_or_fallback()
        elif plot_type == 6:
            from music21.graph.plot import WindowedKey
            wk = WindowedKey(excerpt)
            wk.run()

    def _show_or_fallback(self):
        """Try plt.show(). If it fails, save PNG and let user pick an app to open it."""
        try:
            self._show_or_fallback()
        except Exception:
            import tempfile, os, subprocess
            fd, path = tempfile.mkstemp(suffix='.png', prefix='tta_chart_')
            os.close(fd)
            try:
                plt.gcf().savefig(path, dpi=150, bbox_inches='tight')
            except Exception:
                plt.savefig(path, dpi=150, bbox_inches='tight')
            # Let user choose their own image viewer
            viewer, _ = QFileDialog.getOpenFileName(
                self, "Choose image viewer to open the chart",
                "", "Applications (*.exe *.app);;All Files (*)"
            )
            if viewer:
                subprocess.Popen([viewer, path], shell=True)

    def _generate_plot_win32(self, plot_type: int, part_idx: int, start: int, end: int):
        """Charts for Windows — try plt.show() first, fallback to external viewer."""
        import music21
        try:
            music21.configure.run()
        except Exception:
            pass

        excerpt = self._score.measures(start, end)

        if plot_type == 0:
            # Try music21 notation plot; fallback to pure matplotlib piano roll
            try:
                excerpt.plot(doneAction=None)
            except Exception:
                pitches, offsets, durations = [], [], []
                for el in excerpt.recurse():
                    if isinstance(el, (music21.note.Note, music21.chord.Chord)):
                        o = float(el.offset)
                        d = float(el.quarterLength)
                        if isinstance(el, music21.note.Note):
                            pitches.append(el.pitch.ps)
                            offsets.append(o)
                            durations.append(d)
                        else:
                            for p in el.pitches:
                                pitches.append(p.ps)
                                offsets.append(o)
                                durations.append(d)
                if pitches:
                    plt.barh(pitches, durations, left=offsets, height=0.8,
                             color='steelblue', edgecolor='none')
                    plt.xlabel('Offset (quarterLength)')
                    plt.ylabel('Pitch (MIDI)')
                    plt.title('Note Quarter Length by Pitch')
                else:
                    plt.text(0.5, 0.5, "No notes in selection", ha='center', va='center')
            self._show_or_fallback()

        elif plot_type == 1:
            # Histogram — pitch class distribution
            notes = self._extract_notes(excerpt, part_idx)
            if not notes:
                plt.text(0.5, 0.5, "No notes in selection", ha='center', va='center')
                self._show_or_fallback()
                return
            pcs = [n[0] for n in notes]
            plt.hist(pcs, bins=12, range=(-0.5, 11.5), color='steelblue', edgecolor='white')
            plt.xlabel('Pitch Class')
            plt.ylabel('Count')
            plt.title('Pitch Class Histogram')
            plt.xticks(range(12))
            self._show_or_fallback()

        elif plot_type == 2:
            # Scatter weighted — pitch class × quarterLength
            notes = self._extract_notes(excerpt, part_idx)
            if not notes:
                plt.text(0.5, 0.5, "No notes in selection", ha='center', va='center')
                self._show_or_fallback()
                return
            pcs = [n[0] for n in notes]
            durs = [n[1] for n in notes]
            plt.scatter(pcs, durs, alpha=0.5, s=40, c='steelblue')
            plt.xlabel('Pitch Class')
            plt.ylabel('Quarter Length')
            plt.xticks(range(12))
            plt.title('Scatter: Pitch Class × Quarter Length')
            self._show_or_fallback()

        elif plot_type == 3:
            # Scatter — measure × pitch class
            notes = self._extract_notes(excerpt, part_idx)
            if not notes:
                plt.text(0.5, 0.5, "No notes in selection", ha='center', va='center')
                self._show_or_fallback()
                return
            measures = [n[2] for n in notes]
            pcs = [n[0] for n in notes]
            plt.scatter(measures, pcs, alpha=0.5, s=20, c='steelblue')
            plt.xlabel('Measure')
            plt.ylabel('Pitch Class')
            plt.yticks(range(12))
            plt.title('Pitch Class by Measure')
            self._show_or_fallback()

        elif plot_type == 4:
            # Horizontal bar — duration-weighted pitch class
            src = self._midi_score if self._midi_score else self._score
            notes = self._extract_notes(src.measures(start, end), part_idx)
            if not notes:
                plt.text(0.5, 0.5, "No notes in selection", ha='center', va='center')
                self._show_or_fallback()
                return
            weights = [0.0] * 12
            for pc, dur, _m in notes:
                weights[pc] += dur
            plt.barh(range(12), weights, color='steelblue', edgecolor='white')
            plt.yticks(range(12), [str(i) for i in range(12)])
            plt.xlabel('Total Duration (quarterLength)')
            plt.title('Duration-Weighted Pitch Class')
            self._show_or_fallback()

        elif plot_type == 5:
            # 3D bars from music21 (configure.run() already called above)
            src = self._midi_score if self._midi_score else self._score
            try:
                plot_3d = src.measures(start, end).plot('3dbars', show=False)
                plot_3d.figure.set_size_inches(16, 16)
                plt.tight_layout()
                self._show_or_fallback()
            except Exception:
                # Fall back to 2D bar chart if music21 3D fails
                notes = self._extract_notes(src.measures(start, end), part_idx)
                if not notes:
                    plt.text(0.5, 0.5, "No notes in selection", ha='center', va='center')
                    self._show_or_fallback()
                    return
                pcs = [n[0] for n in notes]
                durs = [n[1] for n in notes]
                plt.bar(range(12), [sum(d for p, d, _ in notes if p == i) for i in range(12)],
                       color='steelblue', edgecolor='white')
                plt.xlabel('Pitch Class')
                plt.ylabel('Total Duration')
                plt.title('Pitch Class Distribution (3D bars unavailable)')
                plt.xticks(range(12))
                self._show_or_fallback()

        elif plot_type == 6:
            # WindowedKey from music21 (configure.run() already called above)
            try:
                from music21.graph.plot import WindowedKey
                wk = WindowedKey(excerpt)
                wk.run()
            except Exception:
                # Pure matplotlib colorgrid fallback
                notes = self._extract_notes(excerpt, part_idx)
                if not notes:
                    plt.text(0.5, 0.5, "No notes in selection", ha='center', va='center')
                    self._show_or_fallback()
                    return
                pcs = [n[0] for n in notes]
                measures = [n[2] for n in notes]
                min_m, max_m = min(measures), max(measures) + 1
                grid = [[0] * 12 for _ in range(min_m, max_m)]
                for pc, m in zip(pcs, measures):
                    if min_m <= m < max_m:
                        grid[m - min_m][pc] += 1
                plt.imshow(list(zip(*grid))[::-1], aspect='auto', cmap='magma',
                          extent=[min_m, max_m, 0, 12])
                plt.xlabel('Measure')
                plt.ylabel('Pitch Class')
                plt.title('Key Analysis (color grid fallback)')
                plt.colorbar(label='Count')
                self._show_or_fallback()

    def _on_save_png(self):
        if self._current_fig is None:
            return
        _plot_names = {
            0: "note_quarter_by_length.png", 1: "histogram.png", 2: "scatter_weighted.png",
            3: "scatter.png", 4: "horizontal_bar.png", 5: "3d_bars.png",
            6: "colorgrid.png",
        }
        default_name = _plot_names.get(getattr(self, '_current_plot_idx', -1), "plot.png")
        path, _ = QFileDialog.getSaveFileName(
            self, tr("viz.save_png"), temp_default_path(default_name),
            "PNG (*.png);;All Files (*)"
        )
        if not path:
            return
        try:
            self._current_fig.savefig(path, dpi=150, bbox_inches='tight')
            QMessageBox.information(self, tr("viz.save_done"),
                                    tr("dialog.saved_to", path=path))
        except Exception as e:
            QMessageBox.critical(self, tr("overview.export_failed"), str(e))
