"""Overview tab: file info, voice diagnosis table, and full-score plot."""

from pathlib import Path

from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QGroupBox, QLabel,
    QTableWidget, QTableWidgetItem, QPushButton, QHeaderView,
    QMessageBox, QFileDialog,
)

from src.core.score_analyzer import (
    diagnose_all_parts, get_measure_range, PartDiagnosis,
)
from src.ui.widgets.score_opener import setup_open_menu
from src.utils.i18n import tr, tr_list


class OverviewTab(QWidget):
    def __init__(self, main_window=None):
        super().__init__()
        self._main_window = main_window
        self._diagnostics: list[PartDiagnosis] = []
        self._setup_ui()

    def _setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(6, 6, 6, 6)

        # Open score button
        top_bar = QHBoxLayout()
        self._btn_open = QPushButton(tr("tab.open_score"))
        setup_open_menu(self._btn_open, self, lambda score, path: self._main_window.set_score(score, path))
        top_bar.addWidget(self._btn_open)
        top_bar.addStretch()
        layout.addLayout(top_bar)

        # File info group
        info_group = QGroupBox(tr("overview.file_info"))
        info_layout = QVBoxLayout(info_group)
        self._lbl_file = QLabel(tr("overview.no_file"))
        info_layout.addWidget(self._lbl_file)
        self._lbl_measures = QLabel("")
        info_layout.addWidget(self._lbl_measures)
        layout.addWidget(info_group)

        # Voice diagnosis table
        diag_group = QGroupBox(tr("overview.diag_group"))
        diag_layout = QVBoxLayout(diag_group)
        headers = tr_list("overview.table.headers")
        self._table = QTableWidget(0, len(headers))
        self._table.setHorizontalHeaderLabels(headers)
        self._table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self._table.setEditTriggers(QTableWidget.NoEditTriggers)
        self._table.setSelectionBehavior(QTableWidget.SelectRows)
        self._table.setMinimumHeight(150)
        diag_layout.addWidget(self._table)
        layout.addWidget(diag_group, 1)

        # Actions
        btn_layout = QHBoxLayout()
        self._btn_full_plot = QPushButton(tr("overview.btn_full_plot"))
        self._btn_full_plot.setProperty("accent", "green")
        self._btn_full_plot.setEnabled(False)
        self._btn_full_plot.clicked.connect(self._on_full_plot)
        btn_layout.addWidget(self._btn_full_plot)

        btn_layout.addStretch()
        layout.addLayout(btn_layout)

    def on_score_loaded(self, score, path: str):
        self._diagnostics = diagnose_all_parts(score)
        self._score = score
        self._path = path

        name = Path(path).name if path else tr("generic.score_name")
        self._lbl_file.setText(tr("overview.file_label", name=name))
        try:
            min_m, max_m = get_measure_range(score)
            parts_count = len(score.parts) if hasattr(score, 'parts') else 1
            self._lbl_measures.setText(
                tr("overview.measures", parts=parts_count, start=min_m, end=max_m)
            )
        except Exception:
            self._lbl_measures.setText("")

        self._populate_table()
        self._btn_full_plot.setEnabled(True)

    def _populate_table(self):
        self._table.setRowCount(len(self._diagnostics))
        for row, d in enumerate(self._diagnostics):
            self._table.setItem(row, 0, QTableWidgetItem(str(d.index + 1)))
            self._table.setItem(row, 1, QTableWidgetItem(d.part_name))
            self._table.setItem(row, 2, QTableWidgetItem(
                ", ".join(d.instruments) if d.instruments else "-"
            ))
            self._table.setItem(row, 3, QTableWidgetItem(str(d.note_count)))
            self._table.setItem(row, 4, QTableWidgetItem(str(d.note_only_count)))
            self._table.setItem(row, 5, QTableWidgetItem(str(d.chord_count)))
            if d.pitch_range:
                range_text = f"{d.pitch_range[0]} - {d.pitch_range[1]}"
            else:
                range_text = "-"
            self._table.setItem(row, 6, QTableWidgetItem(range_text))

    def get_part_names(self) -> list[str]:
        return [d.part_name for d in self._diagnostics]

    def _on_full_plot(self):
        if not self._score:
            return
        try:
            import matplotlib.pyplot as plt
            max_m = get_measure_range(self._score)[1]
            p = self._score.measures(1, max_m).plot(show=False)
            p.figure.set_size_inches(16, 16)
            plt.title(f"Full Score (m.1-{max_m})")
            plt.show()
        except Exception as e:
            QMessageBox.warning(self, tr("overview.plot_error"), str(e))
