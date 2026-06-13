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
from src.ui.theme import default_save_path


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
        from music21 import graph

        if plot_type == 0:
            self._score.measures(start, end).plot()
        elif plot_type == 1:
            self._score.measures(start, end).plot('histogram', 'pitchClass')
        elif plot_type == 2:
            p = graph.plot.ScatterWeightedPitchClassQuarterLength(
                self._score.measures(start, end)
            )
            p.run()
        elif plot_type == 3:
            self._score.measures(start, end).plot('scatter', 'measure', 'pitchClass')
        elif plot_type == 4:
            src = self._midi_score if self._midi_score else self._score
            src.measures(start, end).plot('horizontalbarweighted')
        elif plot_type == 5:
            src = self._midi_score if self._midi_score else self._score
            plot_3d = src.measures(start, end).plot('3dbars', show=False)
            plot_3d.figure.set_size_inches(16, 16)
            plt.tight_layout()
            plt.show()
        elif plot_type == 6:
            from music21.graph.plot import WindowedKey
            wk = WindowedKey(self._score.measures(start, end))
            wk.run()

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
            self, tr("viz.save_png"), default_save_path(default_name),
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
