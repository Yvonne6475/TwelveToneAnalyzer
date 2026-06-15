"""Chord analysis tab: extract chords, classify with Forte, export Markdown/CSV."""

import os
from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QGroupBox, QLabel,
    QCheckBox, QSpinBox, QPushButton, QTableWidget, QTableWidgetItem,
    QHeaderView, QTextEdit, QFileDialog, QMessageBox,
)
from PyQt5.QtCore import Qt

from src.core.chord_analyzer import extract_chords, format_as_markdown, format_as_csv
from src.core.score_analyzer import diagnose_all_parts, get_measure_range
from src.ui.widgets.score_opener import setup_open_menu
from src.utils.i18n import tr, tr_list
from src.ui.theme import default_save_path
from src.utils.config import show_score


def _guess_hand(part) -> str:
    """Guess if a part is right-hand or left-hand based on first-measure clef."""
    try:
        from music21.clef import TrebleClef, BassClef
        measures = part.getElementsByClass('Measure')
        if measures:
            clefs = measures[0].getElementsByClass('Clef')
            if clefs:
                c = clefs[0]
                if isinstance(c, TrebleClef):
                    return " (R.H.)"
                if isinstance(c, BassClef):
                    return " (L.H.)"
    except Exception:
        pass
    return ""


class ChordTab(QWidget):
    def __init__(self, main_window=None):
        super().__init__()
        self._main_window = main_window
        self._score = None
        self._results = []
        self._part_checks = {}
        self._setup_ui()

    def _setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(6, 6, 6, 6)

        # Open score button + info
        top_bar = QHBoxLayout()
        self._btn_open = QPushButton(tr("tab.open_score"))
        setup_open_menu(self._btn_open, self, lambda score, path: self._main_window.set_score(score, path))
        top_bar.addWidget(self._btn_open)
        self._info_label = QLabel("")
        self._info_label.setStyleSheet("color: #888; padding: 4px 8px;")
        top_bar.addWidget(self._info_label)
        top_bar.addStretch()
        layout.addLayout(top_bar)

        filter_group = QGroupBox(tr("chord.filter_group"))
        filter_layout = QVBoxLayout(filter_group)

        part_row = QHBoxLayout()
        part_row.addWidget(QLabel(tr("chord.part_label")))
        self._part_container = QWidget()
        self._part_layout = QHBoxLayout(self._part_container)
        self._part_layout.setContentsMargins(0, 0, 0, 0)
        part_row.addWidget(self._part_container)
        part_row.addStretch()
        filter_layout.addLayout(part_row)

        meas_row = QHBoxLayout()
        meas_row.addWidget(QLabel(tr("chord.start_measure")))
        self._spin_start = QSpinBox()
        self._spin_start.setMinimum(1)
        self._spin_start.setMaximum(999)
        self._spin_start.setValue(1)
        meas_row.addWidget(self._spin_start)
        meas_row.addWidget(QLabel(tr("chord.end_measure")))
        self._spin_end = QSpinBox()
        self._spin_end.setMinimum(1)
        self._spin_end.setMaximum(999)
        self._spin_end.setValue(30)
        meas_row.addWidget(self._spin_end)
        meas_row.addStretch()
        filter_layout.addLayout(meas_row)

        self._btn_extract = QPushButton(tr("chord.btn_extract"))
        self._btn_extract.setProperty("accent", "orange")
        self._btn_extract.setEnabled(False)
        self._btn_extract.clicked.connect(self._on_extract)
        filter_layout.addWidget(self._btn_extract)
        layout.addWidget(filter_group)

        table_group = QGroupBox(tr("chord.result_group"))
        table_layout = QVBoxLayout(table_group)
        headers = tr_list("chord.table.headers")
        self._table = QTableWidget(0, len(headers))
        self._table.setHorizontalHeaderLabels(headers)
        self._table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self._table.setEditTriggers(QTableWidget.NoEditTriggers)
        self._table.setMinimumHeight(150)
        table_layout.addWidget(self._table)
        layout.addWidget(table_group, 1)

        export_row = QHBoxLayout()
        self._btn_export_md = QPushButton(tr("chord.btn_export_md"))
        self._btn_export_md.setEnabled(False)
        self._btn_export_md.clicked.connect(self._on_export_md)
        export_row.addWidget(self._btn_export_md)

        self._btn_export_csv = QPushButton(tr("chord.btn_export_csv"))
        self._btn_export_csv.setEnabled(False)
        self._btn_export_csv.clicked.connect(self._on_export_csv)
        export_row.addWidget(self._btn_export_csv)

        self._btn_show_score = QPushButton(tr("chord.btn_show_score"))
        self._btn_show_score.setEnabled(False)
        self._btn_show_score.clicked.connect(self._on_show_score)
        export_row.addWidget(self._btn_show_score)

        self._btn_save_png = QPushButton(tr("chord.btn_save_png"))
        self._btn_save_png.setEnabled(False)
        self._btn_save_png.clicked.connect(self._on_save_png)
        export_row.addWidget(self._btn_save_png)

        export_row.addStretch()
        layout.addLayout(export_row)

    def on_score_loaded(self, score, path: str):
        self._score = score
        # Clear old chord analysis results — user must re-extract
        self._results = []
        self._table.setRowCount(0)
        max_m = get_measure_range(score)[1]
        self._spin_end.setMaximum(max_m)
        self._spin_end.setValue(min(30, max_m))

        num_parts = len(score.parts) if hasattr(score, 'parts') else 1
        self._info_label.setText(tr("viz.score_info", parts=num_parts, measures=max_m))

        # Clear old checkboxes
        for cb in self._part_checks.values():
            self._part_layout.removeWidget(cb)
            cb.deleteLater()
        self._part_checks.clear()

        # Create checkboxes — one per (part, staff), with smart naming
        diagnostics = diagnose_all_parts(score)
        name_count = {}
        for d in diagnostics:
            base = d.part_name if d.part_name else f"Part {d.index + 1}"
            inst_str = ", ".join(d.instruments) if d.instruments else ""
            is_piano = "piano" in inst_str.lower() or "piano" in base.lower()
            part = score.parts[d.index]

            for s in range(1, max(d.staff_count, 1) + 1):
                display = base
                if d.staff_count >= 2:
                    display = f"{base} (Staff {s})"

                # Detect hand for piano
                if is_piano:
                    if d.staff_count >= 2:
                        display += " (R.H.)" if s == 1 else " (L.H.)"
                    elif name_count.get(base, 0) == 0:
                        hand = _guess_hand(part)
                        display += hand or " (R.H.)"
                    else:
                        display += " (L.H.)"

                # Deduplicate
                if display in name_count:
                    name_count[display] += 1
                    display = f"{display} [{name_count[display]}]"
                else:
                    name_count[display] = 0

                cb = QCheckBox(display)
                cb.setChecked(True)
                cb.setProperty("part_idx", d.index)
                cb.setProperty("staff_idx", s)
                self._part_checks[f"{d.index}:{s}"] = cb
                self._part_layout.addWidget(cb)

        self._btn_extract.setEnabled(True)

    def _on_extract(self):
        if not self._score:
            return
        selected = []
        name_map = {}
        for key, cb in self._part_checks.items():
            if cb.isChecked():
                pi = cb.property("part_idx")
                si = cb.property("staff_idx")
                if pi is not None and si is not None:
                    selected.append((int(pi), int(si)))
                    name_map[(int(pi), int(si))] = cb.text()
        if not selected:
            QMessageBox.warning(self, tr("chord.no_part"), tr("chord.no_part_msg"))
            return

        start = self._spin_start.value()
        end = self._spin_end.value()
        if start > end:
            QMessageBox.warning(self, tr("chord.range_error"), tr("chord.range_error_msg"))
            return

        try:
            self._results = extract_chords(self._score, selected, (start, end), name_map=name_map)
            self._populate_table()
            self._btn_export_md.setEnabled(True)
            self._btn_export_csv.setEnabled(True)
            self._btn_show_score.setEnabled(True)
            self._btn_save_png.setEnabled(True)
        except Exception as e:
            QMessageBox.critical(self, tr("chord.extract_failed"), str(e))

    def _populate_table(self):
        self._table.setRowCount(len(self._results))
        for row, r in enumerate(self._results):
            self._table.setItem(row, 0, QTableWidgetItem(str(r.bar)))
            self._table.setItem(row, 1, QTableWidgetItem(str(r.offset)))
            self._table.setItem(row, 2, QTableWidgetItem(r.part_name))
            self._table.setItem(row, 3, QTableWidgetItem(r.notes))
            self._table.setItem(row, 4, QTableWidgetItem(str(r.pc_set)))
            self._table.setItem(row, 5, QTableWidgetItem(r.forte_class))
            self._table.setItem(row, 6, QTableWidgetItem(r.pitch_range))

    def _on_export_md(self):
        if not self._results:
            return
        path, _ = QFileDialog.getSaveFileName(
            self, tr("chord.save_md"), default_save_path("chord_analysis.md"),
            "Markdown (*.md);;All Files (*)"
        )
        if path:
            with open(path, 'w', encoding='utf-8') as f:
                f.write(format_as_markdown(self._results))
            QMessageBox.information(self, tr("chord.export_done"),
                                    tr("dialog.saved_to", path=path))

    def _on_export_csv(self):
        if not self._results:
            return
        path, _ = QFileDialog.getSaveFileName(
            self, tr("chord.save_csv"), default_save_path("chord_analysis.csv"),
            "CSV (*.csv);;All Files (*)"
        )
        if path:
            with open(path, 'w', encoding='utf-8') as f:
                f.write(format_as_csv(self._results))
            QMessageBox.information(self, tr("chord.export_done"),
                                    tr("dialog.saved_to", path=path))

    def _get_selected_part_indices(self) -> set:
        """Return the set of part indices currently selected in checkboxes."""
        indices = set()
        for key, cb in self._part_checks.items():
            if cb.isChecked():
                pi = cb.property("part_idx")
                if pi is not None:
                    indices.add(int(pi))
        return indices

    def _on_show_score(self):
        if not self._score:
            return
        start = self._spin_start.value()
        end = self._spin_end.value()
        try:
            from music21 import stream
            excerpt = stream.Score()
            part_indices = self._get_selected_part_indices()
            for i, part in enumerate(self._score.parts):
                if i in part_indices:
                    excerpt.insert(0, part.measures(start, end))
            show_score(excerpt)
        except Exception as e:
            QMessageBox.critical(self, tr("overview.plot_error"), str(e))

    def _on_save_png(self):
        if not self._score:
            return
        path, _ = QFileDialog.getSaveFileName(
            self, tr("chord.save_png"), default_save_path("chord_score.png"),
            "PNG (*.png);;All Files (*)"
        )
        if not path:
            return
        start = self._spin_start.value()
        end = self._spin_end.value()
        try:
            from music21 import stream
            excerpt = stream.Score()
            part_indices = self._get_selected_part_indices()
            for i, part in enumerate(self._score.parts):
                if i in part_indices:
                    excerpt.insert(0, part.measures(start, end))
            excerpt.write('musicxml.png', path)
            QMessageBox.information(self, tr("chord.export_done"),
                                    tr("dialog.saved_to", path=path))
        except Exception as e:
            QMessageBox.critical(self, tr("overview.export_failed"), str(e))
