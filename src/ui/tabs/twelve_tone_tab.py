"""Twelve-tone analysis tab: row extraction, P/I/R/RI forms, matrix, row grouping."""

import os
from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QGroupBox, QLabel,
    QComboBox, QPushButton, QTextEdit, QLineEdit,
    QMessageBox, QFileDialog, QScrollArea,
)
from PyQt5.QtCore import Qt
from PyQt5.QtGui import QFont

from src.core.twelve_tone import (
    generate_forms, generate_matrix, make_row_stream,
    divide_into_chords, make_group_stream,
)
from src.core.score_analyzer import (
    extract_first_n_notes, diagnose_all_parts, auto_select_melody_part, get_measure_range,
)
from src.ui.widgets.score_opener import setup_open_menu
from src.ui.widgets.matrix_widget import MatrixWidget
from src.ui.widgets.collapsible_panel import CollapsiblePanel
from src.utils.i18n import tr
from src.ui.theme import default_save_path, matrix_text_stylesheet, monospace_font_family


class TwelveToneTab(QWidget):
    def __init__(self, main_window=None):
        super().__init__()
        self._main_window = main_window
        self._score = None
        self._row = []
        self._last_groups = []
        self._setup_ui()

    def _setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(6, 6, 6, 6)

        # ── Open score button ────────────────────────────────────────
        top_bar = QHBoxLayout()
        self._btn_open = QPushButton(tr("tab.open_score"))
        setup_open_menu(self._btn_open, self, lambda score, path: self._main_window.set_score(score, path))
        top_bar.addWidget(self._btn_open)
        top_bar.addStretch()
        layout.addLayout(top_bar)

        # ── Row extraction (unchanged) ───────────────────────────────
        extract_group = QGroupBox(tr("tt.extract_group"))
        extract_layout = QVBoxLayout(extract_group)

        top_row = QHBoxLayout()
        top_row.addWidget(QLabel(tr("tt.part_label")))
        self._part_combo = QComboBox()
        top_row.addWidget(self._part_combo, 1)

        self._btn_extract = QPushButton(tr("tt.btn_extract"))
        self._btn_extract.setEnabled(False)
        self._btn_extract.clicked.connect(self._on_extract)
        top_row.addWidget(self._btn_extract)
        top_row.addStretch()
        extract_layout.addLayout(top_row)

        self._extracted_label = QLabel("")
        extract_layout.addWidget(self._extracted_label)

        manual_row = QHBoxLayout()
        manual_row.addWidget(QLabel(tr("tt.manual_label")))
        self._manual_input = QLineEdit()
        self._manual_input.setPlaceholderText("6 8 11 1 4 9 7 10 0 3 5 2")
        manual_row.addWidget(self._manual_input)
        self._btn_confirm = QPushButton(tr("tt.btn_confirm"))
        self._btn_confirm.clicked.connect(self._on_confirm_manual)
        manual_row.addWidget(self._btn_confirm)
        extract_layout.addLayout(manual_row)

        layout.addWidget(extract_group)

        # ── Forms display — large font, scrollable ────────────────────
        forms_group = QGroupBox(tr("tt.forms_group"))
        forms_layout = QVBoxLayout(forms_group)
        self._forms_text = QTextEdit()
        self._forms_text.setReadOnly(True)
        self._forms_text.setMinimumHeight(180)
        self._forms_text.setStyleSheet(
            "font-family: Consolas, monospace; font-size: 16px;"
            "background-color: #fefdfb; color: #2c2c2c;"
        )
        forms_layout.addWidget(self._forms_text)
        layout.addWidget(forms_group)

        # Hidden MatrixWidget — used only for heatmap popup (not inline)
        self._matrix_widget = MatrixWidget(self)
        self._matrix_widget.setVisible(False)

        # ═══════════════════════════════════════════════════════════════
        # 12-Tone Matrix container — music21 pure numeric table always
        # visible.  Heatmap opens as a standalone popup (unchanged).
        # ═══════════════════════════════════════════════════════════════
        matrix_group = QGroupBox(tr("tt.matrix_group"))
        matrix_layout = QVBoxLayout(matrix_group)

        # Numeric matrix — uses music21.serial.TwelveToneRow.matrix()
        # True monospace font via QFont for reliable column alignment
        self._matrix_numeric = QTextEdit()
        self._matrix_numeric.setReadOnly(True)
        self._matrix_numeric.setMinimumHeight(200)
        self._matrix_numeric.setLineWrapMode(QTextEdit.NoWrap)
        _family_str = monospace_font_family().replace('"', '').split(",")[0].strip()
        _mono_font = QFont(_family_str)
        _mono_font.setPointSize(13)
        _mono_font.setStyleHint(QFont.Monospace)
        self._matrix_numeric.setFont(_mono_font)
        self._matrix_numeric.document().setDefaultFont(_mono_font)
        # Apply color/background separately (no font-family override)
        self._matrix_numeric.setStyleSheet(
            "QTextEdit {"
            "background-color: #fefdfb;"
            "color: #2c2c2c;"
            "selection-background-color: #d4c8b0;"
            "selection-color: #2c2c2c;"
            "}"
        )
        matrix_layout.addWidget(self._matrix_numeric)

        layout.addWidget(matrix_group, 6)

        # ═══════════════════════════════════════════════════════════════
        # Row Grouping — reusable CollapsiblePanel (cross-platform)
        # The panel is hidden by default and toggled via a button below.
        # On both Windows and macOS the interaction is identical;
        # only the title-bar styling is platform-adaptive (inside the
        # CollapsiblePanel widget).
        # ═══════════════════════════════════════════════════════════════
        self._row_panel = CollapsiblePanel(
            title=tr("tt.btn_dividing_panel"), parent=self, visible=False,
        )
        panel_content = self._row_panel.content_layout()

        # --- Row grouping content (unchanged) ---
        row_group = QGroupBox(tr("tt.row_group"))
        row_layout = QVBoxLayout(row_group)

        btn_row = QHBoxLayout()
        self._btn_trichords = QPushButton(tr("tt.btn_trichords"))
        self._btn_trichords.setEnabled(False)
        self._btn_trichords.clicked.connect(lambda: self._on_divide(3))
        btn_row.addWidget(self._btn_trichords)

        self._btn_tetrachords = QPushButton(tr("tt.btn_tetrachords"))
        self._btn_tetrachords.setEnabled(False)
        self._btn_tetrachords.clicked.connect(lambda: self._on_divide(4))
        btn_row.addWidget(self._btn_tetrachords)

        self._btn_hexachords = QPushButton(tr("tt.btn_hexachords"))
        self._btn_hexachords.setEnabled(False)
        self._btn_hexachords.clicked.connect(lambda: self._on_divide(6))
        btn_row.addWidget(self._btn_hexachords)
        btn_row.addStretch()
        row_layout.addLayout(btn_row)

        self._row_result = QTextEdit()
        self._row_result.setReadOnly(True)
        self._row_result.setMaximumHeight(100)
        self._row_result.setMinimumHeight(60)
        row_layout.addWidget(self._row_result)

        show_row = QHBoxLayout()
        self._btn_show_row = QPushButton(tr("tt.btn_show_row"))
        self._btn_show_row.setEnabled(False)
        self._btn_show_row.clicked.connect(self._on_show_row)
        show_row.addWidget(self._btn_show_row)

        self._btn_save_row_png = QPushButton(tr("tt.btn_save_row_png"))
        self._btn_save_row_png.setEnabled(False)
        self._btn_save_row_png.clicked.connect(self._on_save_row_png)
        show_row.addWidget(self._btn_save_row_png)
        show_row.addStretch()
        row_layout.addLayout(show_row)

        panel_content.addWidget(row_group)
        layout.addWidget(self._row_panel)

        # ═══════════════════════════════════════════════════════════════
        # Bottom bar: toggle panel + export buttons
        # ═══════════════════════════════════════════════════════════════
        export_row = QHBoxLayout()

        # Toggle button for row dividing panel
        self._btn_toggle_panel = QPushButton(tr("tt.panel_btn_open"))
        self._btn_toggle_panel.setProperty("accent", "teal")
        self._btn_toggle_panel.clicked.connect(self._row_panel.toggle)
        self._row_panel.toggled.connect(self._on_panel_toggled)
        export_row.addWidget(self._btn_toggle_panel)

        export_row.addStretch()

        self._btn_export_forms = QPushButton(tr("tt.btn_export_forms"))
        self._btn_export_forms.setEnabled(False)
        self._btn_export_forms.clicked.connect(self._on_export_forms)
        export_row.addWidget(self._btn_export_forms)

        self._btn_export_heatmap = QPushButton(tr("tt.btn_export_heatmap"))
        self._btn_export_heatmap.setEnabled(False)
        self._btn_export_heatmap.clicked.connect(self._on_export_heatmap)
        export_row.addWidget(self._btn_export_heatmap)

        layout.addLayout(export_row)

    # ── Collapsible panel toggle ────────────────────────────────
    def _on_panel_toggled(self, visible: bool):
        if visible:
            self._btn_toggle_panel.setText(tr("tt.panel_btn_close"))
        else:
            self._btn_toggle_panel.setText(tr("tt.panel_btn_open"))

    def on_score_loaded(self, score, path: str):
        self._score = score
        self._part_combo.clear()
        self._part_combo.addItem(tr("viz.all_parts"), -1)
        diagnostics = diagnose_all_parts(score)
        for d in diagnostics:
            self._part_combo.addItem(f"{d.part_name}", d.index)
        if diagnostics:
            best_idx = auto_select_melody_part(score, diagnostics)
            self._part_combo.setCurrentIndex(best_idx + 1 if best_idx + 1 < self._part_combo.count() else 0)
        self._btn_extract.setEnabled(True)
        self._btn_confirm.setEnabled(True)

    def _on_extract(self):
        if not self._score:
            return
        try:
            part_idx = self._part_combo.currentData()
            if part_idx is None:
                return
            if part_idx == -1:
                # All parts — extract sequentially from all parts
                notes = []
                if hasattr(self._score, 'parts'):
                    for part in self._score.parts:
                        notes.extend(extract_first_n_notes(part, 12))
                        if len(notes) >= 12:
                            break
                else:
                    notes = extract_first_n_notes(self._score, 12)
            elif hasattr(self._score, 'parts'):
                notes = extract_first_n_notes(self._score.parts[part_idx], 12)
            else:
                notes = extract_first_n_notes(self._score, 12)

            notes = notes[:12]
            display = ", ".join([f"{name}({pc})" for name, pc in notes])
            self._extracted_label.setText(f"Extracted: {display}")
            self._row = [pc for _, pc in notes]
            self._manual_input.setText(" ".join(map(str, self._row)))
            self._update_analysis()
        except Exception as e:
            QMessageBox.warning(self, tr("tt.extract_failed"), str(e))

    def _on_confirm_manual(self):
        text = self._manual_input.text().strip()
        if not text:
            return
        try:
            text = text.replace(",", " ").replace(";", " ")
            nums = list(map(int, text.split()))
            if len(nums) != 12:
                QMessageBox.warning(self, tr("tt.input_error"), tr("tt.input_count_err", count=str(len(nums))))
                return
            if not all(0 <= x <= 11 for x in nums):
                QMessageBox.warning(self, tr("tt.input_error"), tr("tt.input_range_err"))
                return
            self._row = nums
            self._update_analysis()
        except ValueError:
            QMessageBox.warning(self, tr("tt.input_error"), tr("tt.input_format_err"))

    def _update_analysis(self):
        if not self._row:
            return
        forms = generate_forms(self._row)
        text = ""
        for label, row_data in forms.items():
            text += f"{label} = {row_data}\n"
        self._forms_text.setText(text)
        # Heatmap — auto-popup in standalone window; prompt save on close
        import matplotlib.pyplot as _plt
        _plt.close('all')
        self._matrix_widget.show_matrix(self._row, block=False)

        # Detect when heatmap window is closed → prompt save
        _fig_num = getattr(self._matrix_widget, '_heatmap_num', None)

        def _check_close():
            if _fig_num is None or not _plt.fignum_exists(_fig_num):
                self._heatmap_timer.stop()
                ans = QMessageBox.question(
                    self, tr("tt.matrix_group"),
                    tr("tt.heatmap_save_prompt"),
                    QMessageBox.Yes | QMessageBox.No, QMessageBox.Yes,
                )
                if ans == QMessageBox.Yes:
                    path, _ = QFileDialog.getSaveFileName(
                        self, tr("tt.export_matrix"),
                        default_save_path("12_tone_matrix_heatmap.png"),
                        "PNG (*.png);;All Files (*)",
                    )
                    if path:
                        self._matrix_widget.fig.savefig(path, dpi=300)
                        QMessageBox.information(
                            self, tr("tt.matrix_group"),
                            tr("tt.matrix_exported", path=path),
                        )
                _plt.close('all')

        from PyQt5.QtCore import QTimer
        self._heatmap_timer = QTimer(self)
        self._heatmap_timer.timeout.connect(_check_close)
        self._heatmap_timer.start(300)

        # Numeric matrix — uses generate_matrix (preserves original P row order)
        matrix = generate_matrix(self._row)

        lines = []

        # Pitch-class display: 0-9 as numbers, 10→A, 11→B (music21 native)
        _PC_NAMES = [' 0',' 1',' 2',' 3',' 4',' 5',' 6',' 7',' 8',' 9',' A',' B']

        def _pc_label(pc):
            return _PC_NAMES[pc % 12]

        def _edge(letter, pc):
            v = pc % 12
            if v == 10:
                s = 'A'
            elif v == 11:
                s = 'B'
            else:
                s = str(v)
            return f"{letter}{s:>2}"

        COL_GAP = "  "
        PAD = " " * 6

        # I header row (top) — one I label per column
        i_labels = [_edge("I", matrix[0][j]) for j in range(12)]
        lines.append(PAD + COL_GAP.join(f"{lbl:>4}" for lbl in i_labels))

        # Data rows — P on left, R on right
        for i, r in enumerate(matrix):
            prefix = _edge("P", r[0])
            suffix = _edge("R", r[-1])
            cells = COL_GAP.join(f"{_pc_label(v):>4}" for v in r)
            lines.append(f"{prefix}  {cells}  {suffix}")

        # RI footer row
        ri_labels = [_edge("RI", matrix[-1][j]) for j in range(12)]
        lines.append(PAD + COL_GAP.join(f"{lbl:>4}" for lbl in ri_labels))

        self._matrix_numeric.setText("\n".join(lines))

        for btn in [self._btn_trichords, self._btn_tetrachords, self._btn_hexachords,
                     self._btn_export_forms, self._btn_export_heatmap]:
            btn.setEnabled(True)

    def _on_divide(self, group_size: int):
        if not self._row:
            return
        # Auto-expand the row grouping panel so the user sees the result
        if not self._row_panel.isVisible():
            self._row_panel.expand()
        self._last_groups = divide_into_chords(self._row, group_size)
        lines = []
        for i, c in enumerate(self._last_groups):
            lines.append(
                f"Group {i+1}: {c['notes']}  "
                f"Prime: {c['prime_form']}  Forte: {c['forte_class']}"
            )
        self._row_result.setText("\n".join(lines))
        self._btn_show_row.setEnabled(True)
        self._btn_save_row_png.setEnabled(True)

    def _get_output_dir(self) -> str:
        mw = self._main_window
        return mw.temp_dir if mw else "D:/dev/temp"

    def _on_export_forms(self):
        if not self._row:
            return
        output_dir = QFileDialog.getExistingDirectory(
            self, tr("tt.export_forms"), ""
        )
        if not output_dir:
            return
        forms = generate_forms(self._row)
        for label, row_data in forms.items():
            part = make_row_stream(row_data, label)
            png_path = os.path.join(output_dir, f"{label}.png")
            part.write("musicxml.png", png_path)
        QMessageBox.information(self, tr("tt.forms_group"),
                                tr("tt.forms_exported", path=output_dir))

    def _on_export_heatmap(self):
        """Export the heatmap figure as PNG (same as old popup matrix)."""
        if not self._row:
            return
        if self._matrix_widget.fig is None:
            QMessageBox.warning(self, tr("tt.matrix_group"),
                                "Please open the heatmap first by clicking 'Show Matrix'.")
            return
        path, _ = QFileDialog.getSaveFileName(
            self, tr("tt.export_matrix"), default_save_path("12_tone_matrix_heatmap.png"),
            "PNG (*.png);;All Files (*)"
        )
        if not path:
            return
        self._matrix_widget.fig.savefig(path, dpi=300)
        QMessageBox.information(self, tr("tt.matrix_group"),
                                tr("tt.matrix_exported", path=path))

    def _on_show_row(self):
        if not self._last_groups:
            return
        try:
            s = make_group_stream(self._last_groups)
            s.show()
        except Exception as e:
            QMessageBox.critical(self, tr("overview.plot_error"), str(e))

    def _on_save_row_png(self):
        if not self._last_groups:
            return
        path, _ = QFileDialog.getSaveFileName(
            self, tr("tt.save_row_png"), default_save_path("row_groups.png"),
            "PNG (*.png);;All Files (*)"
        )
        if not path:
            return
        try:
            s = make_group_stream(self._last_groups)
            s.write('musicxml.png', path)
            QMessageBox.information(self, tr("tt.save_row_png"),
                                    tr("tt.row_png_saved", path=path))
        except Exception as e:
            QMessageBox.critical(self, tr("overview.export_failed"), str(e))
