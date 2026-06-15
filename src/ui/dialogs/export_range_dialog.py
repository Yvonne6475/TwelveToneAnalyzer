"""Export annotated score dialog: select measure range, preview, and export."""

import os
from pathlib import Path
from datetime import datetime

from PyQt5.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QFormLayout, QSpinBox,
    QLabel, QPushButton, QDialogButtonBox, QMessageBox,
)
from PyQt5.QtCore import Qt

from src.core.score_analyzer import annotate_score
from src.utils.i18n import tr
from src.utils.config import show_score


class ExportAnnotatedDialog(QDialog):
    """Standalone dialog for previewing and exporting annotated score excerpts."""

    def __init__(self, score, score_path: str, output_dir: str,
                 max_measure: int, parent=None):
        super().__init__(parent)
        self._score = score
        self._score_path = score_path
        self._output_dir = output_dir
        self._max_measure = max_measure
        self._setup_ui()

    def _setup_ui(self):
        self.setWindowTitle(tr("dialog.export_range_title"))
        self.setMinimumWidth(520)
        self.setWindowFlags(self.windowFlags() & ~Qt.WindowContextHelpButtonHint)

        layout = QVBoxLayout(self)
        layout.setSpacing(12)

        # Range info
        info = QLabel(tr("dialog.export_range_label",
                        min=1, max=self._max_measure))
        info.setStyleSheet("font-weight: bold;")
        layout.addWidget(info)

        # Measure range inputs
        form = QFormLayout()
        self._spin_start = QSpinBox()
        self._spin_start.setMinimum(1)
        self._spin_start.setMaximum(self._max_measure)
        self._spin_start.setValue(1)
        form.addRow(tr("viz.start_measure"), self._spin_start)

        self._spin_end = QSpinBox()
        self._spin_end.setMinimum(1)
        self._spin_end.setMaximum(self._max_measure)
        self._spin_end.setValue(min(50, self._max_measure))
        form.addRow(tr("viz.end_measure"), self._spin_end)
        layout.addLayout(form)

        # Action buttons
        btn_row = QHBoxLayout()

        self._btn_preview = QPushButton(tr("dialog.export_preview"))
        self._btn_preview.setProperty("accent", "teal")
        self._btn_preview.clicked.connect(self._on_preview)
        btn_row.addWidget(self._btn_preview)

        self._btn_export = QPushButton(tr("dialog.export_do_export"))
        self._btn_export.setProperty("accent", "green")
        self._btn_export.clicked.connect(self._on_export)
        btn_row.addWidget(self._btn_export)

        btn_row.addStretch()
        layout.addLayout(btn_row)

        # Close button
        dbb = QDialogButtonBox(QDialogButtonBox.Close)
        dbb.rejected.connect(self.reject)
        layout.addWidget(dbb)

    def _validate(self) -> bool:
        if self._spin_start.value() > self._spin_end.value():
            QMessageBox.warning(self, tr("viz.range_error"),
                                tr("viz.range_error_msg"))
            return False
        return True

    def _on_preview(self):
        if not self._validate():
            return
        try:
            excerpt = annotate_score(
                self._score,
                self._spin_start.value(),
                self._spin_end.value()
            )
            show_score(excerpt)
        except Exception as e:
            QMessageBox.critical(self, tr("overview.plot_error"), str(e))

    def _on_export(self):
        if not self._validate():
            return
        try:
            os.makedirs(self._output_dir, exist_ok=True)

            excerpt = annotate_score(
                self._score,
                self._spin_start.value(),
                self._spin_end.value()
            )

            piece_name = Path(self._score_path).stem if self._score_path else "analysis"
            date_str = datetime.now().strftime("%Y%m%d")
            start = self._spin_start.value()
            end = self._spin_end.value()
            base = f"{piece_name}_m{start}-{end}_pc_forte_{date_str}"

            xml_path = os.path.join(self._output_dir, f"{base}.musicxml")
            pdf_path = os.path.join(self._output_dir, f"{base}.pdf")

            from src.utils.config import configure_music21_environment
            configure_music21_environment()

            excerpt.write('musicxml', xml_path)
            try:
                excerpt.write('musicxml.pdf', pdf_path)
            except Exception:
                pass  # PDF requires MuseScore

            show_score(excerpt)

            pdf_ok = os.path.exists(pdf_path)
            msg = tr("dialog.export_annotated_msg",
                     xml=xml_path,
                     pdf=pdf_path if pdf_ok else "N/A")
            QMessageBox.information(self, tr("dialog.export_complete"), msg)

        except Exception as e:
            QMessageBox.critical(self, tr("overview.export_failed"), str(e))
