"""Annotated Score tab: add pitch-class/Forte lyrics and export MusicXML+PDF."""

import os
import traceback
from pathlib import Path
from datetime import datetime

from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QFormLayout, QGroupBox,
    QLabel, QSpinBox, QPushButton, QCheckBox, QMessageBox, QFileDialog,
)
from PyQt5.QtCore import Qt

from src.core.score_analyzer import (
    annotate_score, annotate_score_full, get_measure_range,
    strip_annotations, _add_pc_forte_lyrics, clean_xml_presentation,
)
from src.ui.widgets.score_opener import setup_open_menu
from src.utils.i18n import tr


class AnnotatedScoreTab(QWidget):
    def __init__(self, main_window=None):
        super().__init__()
        self._main_window = main_window
        self._score = None
        self._score_path = ""
        self._min_measure = 1
        self._max_measure = 272
        self._is_mei = False
        self._setup_ui()

    def _setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(6, 6, 6, 6)

        # Top bar: open score button
        top_bar = QHBoxLayout()
        self._btn_open = QPushButton(tr("tab.open_score"))
        setup_open_menu(self._btn_open, self, lambda score, path: self._main_window.set_score(score, path))
        top_bar.addWidget(self._btn_open)
        top_bar.addStretch()
        layout.addLayout(top_bar)

        # MEI notice (hidden by default, shown only for MEI files)
        self._mei_notice = QLabel(tr("tab.mei_notice"))
        self._mei_notice.setStyleSheet("color: #0c5460; background: #d1ecf1; "
                                        "border: 1px solid #17a2b8; border-radius: 4px; "
                                        "padding: 8px 12px; font-size: 14px;")
        self._mei_notice.setWordWrap(True)
        self._mei_notice.hide()
        layout.addWidget(self._mei_notice)

        # Range selection group
        self._range_group = QGroupBox(tr("dialog.export_range_title"))
        range_layout = QVBoxLayout(self._range_group)

        self._range_info = QLabel(tr("tab.no_score_loaded"))
        self._range_info.setStyleSheet("font-weight: bold;")
        range_layout.addWidget(self._range_info)

        form = QFormLayout()
        self._spin_start = QSpinBox()
        self._spin_start.setMinimum(self._min_measure)
        self._spin_start.setMaximum(self._max_measure)
        self._spin_start.setValue(self._min_measure)
        self._spin_start.setEnabled(False)
        form.addRow(tr("viz.start_measure"), self._spin_start)

        self._spin_end = QSpinBox()
        self._spin_end.setMinimum(self._min_measure)
        self._spin_end.setMaximum(self._max_measure)
        self._spin_end.setValue(min(self._min_measure + 49, self._max_measure))
        self._spin_end.setEnabled(False)
        form.addRow(tr("viz.end_measure"), self._spin_end)
        range_layout.addLayout(form)

        layout.addWidget(self._range_group)

        # Export options
        export_opts = QHBoxLayout()
        self._chk_strip = QCheckBox(tr("tab.strip_annotations"))
        self._chk_strip.setToolTip(tr("tab.strip_annotations_tip"))
        export_opts.addWidget(self._chk_strip)
        export_opts.addStretch()
        layout.addLayout(export_opts)

        # Action buttons
        btn_row = QHBoxLayout()

        self._btn_preview = QPushButton(tr("dialog.export_preview"))
        self._btn_preview.setProperty("accent", "teal")
        self._btn_preview.setEnabled(False)
        self._btn_preview.clicked.connect(self._on_preview)
        btn_row.addWidget(self._btn_preview)

        self._btn_export = QPushButton(tr("dialog.export_do_export"))
        self._btn_export.setProperty("accent", "green")
        self._btn_export.setEnabled(False)
        self._btn_export.clicked.connect(self._on_export)
        btn_row.addWidget(self._btn_export)

        btn_row.addStretch()
        layout.addLayout(btn_row)
        layout.addStretch()

    def on_score_loaded(self, score=None, path=None):
        if score is None:
            return
        self._score = score
        self._score_path = path or ""

        self._is_mei = path and path.endswith('.mei')
        self._mei_notice.setVisible(self._is_mei)

        if self._is_mei:
            # MEI: no measure range, use full score
            self._range_info.setText(tr("tab.mei_full_score"))
            self._range_group.setVisible(False)
        else:
            try:
                self._min_measure, self._max_measure = get_measure_range(score)
            except Exception:
                self._min_measure, self._max_measure = 1, 272
            self._range_info.setText(
                tr("tab.measure_range", min=self._min_measure, max=self._max_measure)
            )
            self._spin_start.setMinimum(self._min_measure)
            self._spin_start.setMaximum(self._max_measure)
            self._spin_start.setValue(self._min_measure)
            self._spin_end.setMinimum(self._min_measure)
            self._spin_end.setMaximum(self._max_measure)
            self._spin_end.setValue(min(self._min_measure + 49, self._max_measure))
            self._spin_start.setEnabled(True)
            self._spin_end.setEnabled(True)
            self._range_group.setVisible(True)

        self._btn_preview.setEnabled(True)
        self._btn_export.setEnabled(True)

    def _validate(self) -> bool:
        if self._is_mei:
            return True
        if self._spin_start.value() > self._spin_end.value():
            QMessageBox.warning(self, tr("viz.range_error"),
                                tr("viz.range_error_msg"))
            return False
        return True

    def _get_output_dir(self) -> str:
        mw = self._main_window
        return mw.temp_dir if mw else "D:/dev/temp"

    def _on_preview(self):
        if not self._validate():
            return
        try:
            if self._is_mei:
                if self._chk_strip.isChecked():
                    strip_annotations(self._score)
                _add_pc_forte_lyrics(self._score)
                excerpt = self._score
            else:
                excerpt = self._score.measures(
                    self._spin_start.value(),
                    self._spin_end.value()
                )
                if self._chk_strip.isChecked():
                    strip_annotations(excerpt)
                _add_pc_forte_lyrics(excerpt)
            excerpt.show()
        except Exception as e:
            QMessageBox.critical(self, tr("overview.plot_error"), str(e))

    def _on_export(self):
        if not self._validate():
            return
        output_dir = QFileDialog.getExistingDirectory(
            self, tr("dialog.export_range_title"), ""
        )
        if not output_dir:
            return
        try:

            if self._is_mei:
                # MEI: work on full score (measures not supported)
                if self._chk_strip.isChecked():
                    strip_annotations(self._score)
                _add_pc_forte_lyrics(self._score)
                excerpt = self._score
            else:
                excerpt = self._score.measures(
                    self._spin_start.value(),
                    self._spin_end.value()
                )
                if self._chk_strip.isChecked():
                    strip_annotations(excerpt)
                _add_pc_forte_lyrics(excerpt)

            piece_name = Path(self._score_path).stem if self._score_path else "analysis"
            date_str = datetime.now().strftime("%Y%m%d")

            if self._is_mei:
                base = f"{piece_name}_full_pc_forte_{date_str}"
            else:
                start = self._spin_start.value()
                end = self._spin_end.value()
                base = f"{piece_name}_m{start}-{end}_pc_forte_{date_str}"

            xml_path = os.path.join(output_dir, f"{base}.musicxml")
            pdf_path = os.path.join(output_dir, f"{base}.pdf")

            excerpt.write('musicxml', xml_path)

            if self._chk_strip.isChecked():
                clean_xml_presentation(xml_path)

            try:
                excerpt.write('musicxml.pdf', pdf_path)
            except Exception:
                pass

            excerpt.show()

            pdf_ok = os.path.exists(pdf_path)
            msg = tr("dialog.export_annotated_msg",
                     xml=xml_path,
                     pdf=pdf_path if pdf_ok else "N/A")
            QMessageBox.information(self, tr("dialog.export_complete"), msg)

        except Exception as e:
            QMessageBox.critical(self, tr("overview.export_failed"), str(e))
