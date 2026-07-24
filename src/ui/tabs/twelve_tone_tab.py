"""Twelve-tone analysis tab: row extraction, P/I/R/RI forms, matrix, row grouping."""

import os
from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QGroupBox, QLabel,
    QComboBox, QPushButton, QTextEdit, QLineEdit, QDialog, QSpinBox,
    QCheckBox, QMessageBox, QFileDialog, QScrollArea,
)
from PyQt5.QtCore import Qt
from PyQt5.QtGui import QFont

from music21 import chord
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
from src.utils.config import show_score, temp_default_path, get_temp_dir
from src.ui.theme import matrix_text_stylesheet, monospace_font_family



class RowDivisionDialog(QDialog):
    """Dialog for dividing a 12-tone row into equal-sized groups."""

    def __init__(self, row: list[int], parent=None):
        super().__init__(parent)
        self._row = row
        self._last_groups = []
        self.setWindowTitle(tr("tt.row_group"))
        self.setMinimumSize(520, 380)
        self._setup_ui()

    def _setup_ui(self):
        layout = QVBoxLayout(self)
        size_row = QHBoxLayout()
        size_row.addWidget(QLabel(tr("tt.dlg_group_size")))
        self._spin_size = QSpinBox()
        self._spin_size.setMinimum(1)
        self._spin_size.setMaximum(12)
        self._spin_size.setValue(3)
        self._spin_size.valueChanged.connect(self._do_divide)
        size_row.addWidget(self._spin_size)
        size_row.addStretch()
        layout.addLayout(size_row)
        self._result = QTextEdit()
        self._result.setReadOnly(True)
        layout.addWidget(self._result, 1)
        btn_row = QHBoxLayout()
        self._btn_show = QPushButton(tr("chord.btn_show_score"))
        self._btn_show.clicked.connect(self._on_show)
        btn_row.addWidget(self._btn_show)
        self._btn_save = QPushButton(tr("chord.save_png"))
        self._btn_save.clicked.connect(self._on_save)
        btn_row.addWidget(self._btn_save)
        btn_row.addStretch()
        close_btn = QPushButton(tr("forte.btn_close"))
        close_btn.clicked.connect(self.close)
        btn_row.addWidget(close_btn)
        layout.addLayout(btn_row)
        self._do_divide()

    def _do_divide(self):
        gs = self._spin_size.value()
        self._last_groups = divide_into_chords(self._row, gs)
        lines = []
        for i, c in enumerate(self._last_groups):
            lines.append(
                f"Group {i+1}: {c['notes']}  "
                f"Prime: {c['prime_form']}  Forte: {c['forte_class']}"
            )
        if len(self._row) % gs != 0:
            lines.append(
                f"\n(Note: {len(self._row)} not divisible by {gs}, "
                f"last group has {len(self._row) % gs} notes)")
        self._result.setText("\n".join(lines))

    def _on_show(self):
        if not self._last_groups:
            return
        try:
            s = make_group_stream(self._last_groups, "Row Groups")
            show_score(s)
        except Exception as e:
            QMessageBox.critical(self, tr("overview.plot_error"), str(e))

    def _on_save(self):
        if not self._last_groups:
            return
        path, _ = QFileDialog.getSaveFileName(
            self, tr("tt.save_row_png"), temp_default_path("row_groups.png"),
            "PNG (*.png);;All Files (*)")
        if not path:
            return
        try:
            s = make_group_stream(self._last_groups, "Row Groups")
            s.write('musicxml.png', path)
            QMessageBox.information(self, tr("tt.save_row_png"),
                                    tr("tt.row_png_saved", path=path))
        except Exception as e:
            QMessageBox.critical(self, tr("overview.export_failed"), str(e))


class SubsetSearchDialog(QDialog):
    """Dialog for searching a pc-set across all 48 row forms."""

    def __init__(self, row: list[int], parent=None):
        super().__init__(parent)
        self._row = row
        self.setWindowTitle(tr("tt.subset_group"))
        self.setMinimumSize(520, 380)
        self._setup_ui()

    def _setup_ui(self):
        layout = QVBoxLayout(self)
        input_row = QHBoxLayout()
        input_row.addWidget(QLabel(tr("tt.subset_label")))
        self._input = QLineEdit()
        self._input.setPlaceholderText("6 9 11")
        self._input.returnPressed.connect(self._do_search)
        input_row.addWidget(self._input)
        self._btn_search = QPushButton(tr("tt.btn_search_subset"))
        self._btn_search.clicked.connect(self._do_search)
        input_row.addWidget(self._btn_search)
        layout.addLayout(input_row)
        self._result = QTextEdit()
        self._result.setReadOnly(True)
        layout.addWidget(self._result, 1)
        btn_row = QHBoxLayout()
        btn_row.addStretch()
        close_btn = QPushButton(tr("forte.btn_close"))
        close_btn.clicked.connect(self.close)
        btn_row.addWidget(close_btn)
        layout.addLayout(btn_row)

    def _do_search(self):
        if not self._row or len(self._row) != 12:
            QMessageBox.warning(self, tr("tt.subset_group"), tr("tt.subset_no_row"))
            return
        text = self._input.text().strip()
        if not text:
            QMessageBox.warning(self, tr("tt.subset_group"), tr("tt.subset_invalid"))
            return
        try:
            input_set = list(map(int, text.split()))
        except ValueError:
            QMessageBox.warning(self, tr("tt.subset_group"), tr("tt.subset_invalid"))
            return
        if len(input_set) < 3:
            QMessageBox.warning(self, tr("tt.subset_group"), tr("tt.subset_too_short"))
            return
        row = self._row
        pivot = row[0]
        i0 = [(2 * pivot - p) % 12 for p in row]
        r0 = list(reversed(row))
        ri0 = list(reversed(i0))
        set_len = len(input_set)
        input_sorted = sorted(input_set)
        output = []
        for form_type, base in [("P", row), ("I", i0), ("R", r0), ("RI", ri0)]:
            base_start = base[0]
            for tn in range(12):
                form = [(p + tn) % 12 for p in base]
                label_num = (base_start + tn) % 12
                for start in range(12 - set_len + 1):
                    window = form[start:start + set_len]
                    if sorted(window) == input_sorted:
                        output.append(
                            f"{form_type}{label_num}  pos.{start+1}-{start+set_len}:  "
                            f"{' '.join(map(str, window))}")
        self._result.setText("\n".join(output) if output else tr("tt.subset_none"))



class MergeSearchDialog(QDialog):
    """Dialog: merge selected parts & bars, then search for 12-tone rows."""

    def __init__(self, score, main_window=None, row=None):
        super().__init__(main_window)
        self._score = score
        self._main_window = main_window
        self._row = row
        self._part_checks = {}
        self.setWindowTitle(tr("tt.merge_title"))
        self.setMinimumSize(600, 450)
        self._setup_ui()

    def _setup_ui(self):
        layout = QVBoxLayout(self)

        # Part selection
        part_group = QGroupBox(tr("chord.part_label"))
        part_layout = QHBoxLayout(part_group)
        diagnostics = diagnose_all_parts(self._score) if self._score else []
        self._part_checks = {}
        for d in diagnostics:
            part = self._score.parts[d.index] if self._score else None
            display = d.part_name if d.part_name else f"Part {d.index + 1}"
            cb = QCheckBox(display)
            cb.setChecked(True)
            cb.setProperty("part_idx", d.index)
            self._part_checks[f"{d.index}"] = cb
            part_layout.addWidget(cb)
        layout.addWidget(part_group)

        # Bar range
        bar_row = QHBoxLayout()
        bar_row.addWidget(QLabel(tr("chord.start_measure")))
        self._spin_start = QSpinBox()
        self._spin_start.setMinimum(1)
        self._spin_start.setMaximum(999)
        self._spin_start.setValue(1)
        bar_row.addWidget(self._spin_start)
        bar_row.addWidget(QLabel(tr("chord.end_measure")))
        self._spin_end = QSpinBox()
        self._spin_end.setMinimum(1)
        self._spin_end.setMaximum(999)
        self._spin_end.setValue(30)
        bar_row.addWidget(self._spin_end)
        bar_row.addStretch()
        layout.addLayout(bar_row)

        # Search button
        self._btn_search = QPushButton(tr("tt.btn_merge_search"))
        self._btn_search.setProperty("accent", "teal")
        self._btn_search.clicked.connect(self._do_search)
        layout.addWidget(self._btn_search)

        # Results
        self._result = QTextEdit()
        self._result.setReadOnly(True)
        self._result.setMinimumHeight(200)
        layout.addWidget(self._result, 1)

        # Close
        close_btn = QPushButton(tr("forte.btn_close"))
        close_btn.clicked.connect(self.close)
        layout.addWidget(close_btn)

    def _do_search(self):
        if not self._score:
            self._result.setText(tr("tt.merge_no_score"))
            return

        selected_parts = set()
        for key, cb in self._part_checks.items():
            if cb.isChecked():
                pi = cb.property("part_idx")
                if pi is not None:
                    selected_parts.add(int(pi))
        if not selected_parts:
            self._result.setText(tr("tt.merge_no_part"))
            return

        start = self._spin_start.value()
        end = self._spin_end.value()
        if start > end:
            self._result.setText(tr("chord.range_error_msg"))
            return

        from music21 import note as m21note
        from collections import OrderedDict

        # Gather all notes with part & bar info
        all_notes = []  # (offset, pc, part_name, bar, part_idx)
        for pi, part in enumerate(self._score.parts):
            if pi not in selected_parts:
                continue
            pn = part.partName if part.partName else f"Part {pi+1}"
            meas_all = list(part.getElementsByClass("Measure"))
            meas_range = [m for m in meas_all if start <= m.number <= end]
            if not meas_range:
                continue
            for _i in range(1, len(meas_range)):
                if meas_range[_i].getOffsetBySite(part) - meas_range[_i-1].getOffsetBySite(part) > 10000:
                    meas_range = meas_range[:_i]
                    break
            for m in meas_range:
                bn = m.number
                for el in m.notes:
                    global_off = m.offset + el.offset  # global offset
                    if isinstance(el, chord.Chord):
                        for p in el.pitches:
                            all_notes.append((global_off, p.pitchClass, pn, bn, pi))
                    elif isinstance(el, m21note.Note):
                        all_notes.append((global_off, el.pitch.pitchClass, pn, bn, pi))
        all_notes.sort(key=lambda x: (x[3], x[0]))  # sort by bar, then offset

        if not all_notes:
            self._result.setText(tr("tt.merge_no_notes"))
            return

        pc_seq = [pc for _, pc, *_ in all_notes]
        output = []

        # --- Per-bar, per-part breakdown ---
        bar_parts = OrderedDict()
        for off, pc, pn, bn, pi in all_notes:
            bar_parts.setdefault(bn, OrderedDict()).setdefault(pn, []).append(pc)
        output.append("=== Per-Bar Part Breakdown ===")
        for bar in sorted(bar_parts):
            bar_cons = bar_parts[bar]
            output.append(f"\n--- Bar {bar} ---")
            for pn in bar_cons:
                pcs = bar_cons[pn]
                unique_pcs = list(dict.fromkeys(pcs))  # preserve order, dedup
                fc = chord.Chord(unique_pcs).forteClass if len(unique_pcs) > 1 else ""
                output.append(f"  {pn}: {' '.join(map(str, unique_pcs))}  Forte: {fc}" if fc else f"  {pn}: {' '.join(map(str, unique_pcs))}")
            # Bar merged (union of all parts in this bar)
            bar_all_pcs = []
            for pcs in bar_cons.values():
                bar_all_pcs.extend(pcs)
            bar_merged = list(dict.fromkeys(bar_all_pcs))
            bar_fc = chord.Chord(bar_merged).forteClass if len(bar_merged) > 1 else ""
            output.append(f"  Merged (bar {bar}): {' '.join(map(str, bar_merged))}  Forte: {bar_fc}" if bar_fc else f"  Merged (bar {bar}): {' '.join(map(str, bar_merged))}")

        # --- Merged PC sequence ---
        unique_count = len(set(pc_seq))
        unique_pcs_all = list(dict.fromkeys(pc_seq))  # appearance order
        output.append(f"\n=== Merged PC Sequence ({len(pc_seq)} notes, {unique_count}/12 unique) ===")
        output.append(' '.join(map(str, pc_seq)))
        output.append(f"Unique ({len(unique_pcs_all)}): {' '.join(map(str, unique_pcs_all))}")

        # Per-part unique PCs
        from collections import OrderedDict
        part_data = OrderedDict()
        for off, pc, pn, bn, pi in all_notes:
            part_data.setdefault(pn, []).append(pc)
        output.append("\n=== Per-Part Unique PCs ===")
        per_part_parts = []
        for pn in part_data:
            pcs = part_data[pn]
            uniq = list(dict.fromkeys(pcs))
            per_part_parts.append(f"{pn} [{', '.join(map(str, uniq))}]")
        output.append("  ".join(per_part_parts))

        # Match against the 48 forms of the confirmed row
        if self._row and len(unique_pcs_all) == 12:
            row = self._row
            pivot = row[0]
            i0 = [(2 * pivot - p) % 12 for p in row]
            r0 = list(reversed(row))
            ri0 = list(reversed(i0))
            output.append("\n=== Matching Confirm Row Forms ===")
            matched = False
            for form_type, base in [("P", row), ("I", i0), ("R", r0), ("RI", ri0)]:
                base_start = base[0]
                for tn in range(12):
                    form = [(p + tn) % 12 for p in base]
                    if form == unique_pcs_all:
                        label_num = (base_start + tn) % 12
                        output.append(f"  ✓ {form_type}{label_num}: {' '.join(map(str, form))}")
                        matched = True
            if not matched:
                output.append("  (no match among 48 forms)")

        # --- 12-tone row search ---
        if len(pc_seq) >= 12:
            found = False
            for start_idx in range(len(pc_seq) - 12 + 1):
                window = pc_seq[start_idx:start_idx + 12]
                if sorted(window) == list(range(12)):
                    found = True
                    row = list(window)
                    pivot = row[0]
                    i0 = [(2 * pivot - p) % 12 for p in row]
                    r0 = list(reversed(row))
                    ri0 = list(reversed(i0))
                    output.append(f"\n--- 12-tone row at notes {start_idx+1}-{start_idx+12} ---")
                    output.append(f"P{pivot}: {' '.join(map(str, row))}")
                    output.append(f"I{pivot}: {' '.join(map(str, i0))}")
                    output.append(f"R{row[-1]}: {' '.join(map(str, r0))}")
                    output.append(f"RI{i0[-1]}: {' '.join(map(str, ri0))}")
            if not found:
                output.append(f"\nNo complete 12-tone row (only {unique_count}/12 unique PCs).")
        else:
            output.append(f"\nOnly {len(pc_seq)} notes — need at least 12 for a row.")

        self._result.setText("\n".join(output))



class CustomMergeDialog(QDialog):
    """Dialog: select arbitrary parts + bar list, merge into a single set."""

    def __init__(self, score, main_window=None, row=None):
        super().__init__(main_window)
        self._score = score
        self._main_window = main_window
        self._row = row
        self._part_checks = {}
        self.setWindowTitle(tr("tt.custom_merge_title"))
        self.setMinimumSize(650, 500)
        self._setup_ui()

    def _setup_ui(self):
        layout = QVBoxLayout(self)

        # Part selection
        part_group = QGroupBox(tr("chord.part_label"))
        part_layout = QHBoxLayout(part_group)
        diagnostics = diagnose_all_parts(self._score) if self._score else []
        self._part_checks = {}
        for d in diagnostics:
            cb = QCheckBox(d.part_name if d.part_name else f"Part {d.index+1}")
            cb.setChecked(True)
            cb.setProperty("part_idx", d.index)
            self._part_checks[f"{d.index}"] = cb
            part_layout.addWidget(cb)
        layout.addWidget(part_group)

        # Bar list input
        bar_row = QHBoxLayout()
        bar_row.addWidget(QLabel(tr("tt.custom_bars_label")))
        self._bars_input = QLineEdit()
        self._bars_input.setPlaceholderText("1, 3, 5-10, 12, 15-20")
        self._bars_input.setText("1-30")
        bar_row.addWidget(self._bars_input)
        layout.addLayout(bar_row)

        # Merge button
        self._btn_merge = QPushButton(tr("tt.btn_custom_merge"))
        self._btn_merge.setProperty("accent", "teal")
        self._btn_merge.clicked.connect(self._do_merge)
        layout.addWidget(self._btn_merge)

        # Results
        self._result = QTextEdit()
        self._result.setReadOnly(True)
        layout.addWidget(self._result, 1)

        # Close
        btn_row = QHBoxLayout()
        btn_row.addStretch()
        close_btn = QPushButton(tr("forte.btn_close"))
        close_btn.clicked.connect(self.close)
        btn_row.addWidget(close_btn)
        layout.addLayout(btn_row)

    def _parse_bars(self, text: str) -> list[int]:
        """Parse bar list: '1,3,5-10,12' -> [1,3,5,6,7,8,9,10,12]."""
        bars = set()
        for part in text.split(","):
            part = part.strip()
            if not part:
                continue
            if "-" in part:
                try:
                    a, b = part.split("-", 1)
                    lo, hi = int(a.strip()), int(b.strip())
                    bars.update(range(lo, hi + 1))
                except ValueError:
                    pass
            else:
                try:
                    bars.add(int(part))
                except ValueError:
                    pass
        return sorted(bars)

    def _do_merge(self):
        if not self._score:
            self._result.setText(tr("tt.merge_no_score"))
            return

        selected_parts = set()
        for key, cb in self._part_checks.items():
            if cb.isChecked():
                pi = cb.property("part_idx")
                if pi is not None:
                    selected_parts.add(int(pi))
        if not selected_parts:
            self._result.setText(tr("tt.merge_no_part"))
            return

        bars = self._parse_bars(self._bars_input.text().strip())
        if not bars:
            self._result.setText(tr("tt.custom_bars_invalid"))
            return

        from music21 import note as m21note
        from collections import OrderedDict

        # Collect notes by (part, bar)
        data = OrderedDict()  # part_name -> {bar -> [pc]}
        all_pcs = []
        for pi, part in enumerate(self._score.parts):
            if pi not in selected_parts:
                continue
            pn = part.partName if part.partName else f"Part {pi+1}"
            data[pn] = OrderedDict()
            meas_all = list(part.getElementsByClass('Measure'))
            meas_range = [m for m in meas_all if m.number in bars]
            if not meas_range:
                continue
            for m in meas_range:
                bn = m.number
                for el in m.recurse():
                    if isinstance(el, m21note.Note):
                        data[pn].setdefault(bn, []).append(el.pitch.pitchClass)
                        all_pcs.append(el.pitch.pitchClass)
                    elif isinstance(el, chord.Chord):
                        for p in el.pitches:
                            data[pn].setdefault(bn, []).append(p.pitchClass)
                            all_pcs.append(p.pitchClass)

        output = []
        selected_bars_str = ", ".join(str(b) for b in bars)
        selected_parts_str = ", ".join(
            cb.text() for cb in self._part_checks.values() if cb.isChecked()
        )
        output.append(f"Selected: {selected_parts_str} | Bars: {selected_bars_str}\n")

        # Per-part / per-bar breakdown
        for pn in data:
            output.append(f"--- {pn} ---")
            part_all = []
            for bn in data[pn]:
                pcs = data[pn][bn]
                uniq = list(dict.fromkeys(pcs))
                fc = chord.Chord(uniq).forteClass if len(uniq) > 1 else ""
                orig = list(dict.fromkeys(pcs))
                output.append(f"  Bar {bn}: {' '.join(map(str, orig))}  Forte: {fc}" if fc else f"  Bar {bn}: {' '.join(map(str, orig))}")
                part_all.extend(pcs)
            # Part Merge: aggregate all bars for this part
            part_merged = list(dict.fromkeys(part_all))
            part_bars_seen = []
            part_seq = []
            seen_set = set()
            for bn in data[pn]:
                for pc in data[pn][bn]:
                    if pc not in seen_set:
                        part_seq.append(pc)
                        seen_set.add(pc)
                part_bars_seen.append(bn)
            bar_range = f"Bars {min(part_bars_seen)}-{max(part_bars_seen)}" if part_bars_seen else ""
            if len(part_merged) > 1:
                fc_part = chord.Chord(sorted(part_merged)).forteClass
                output.append(f"  >> Part Merge {bar_range}: {' '.join(map(str, part_seq))}  Forte: {fc_part}")

        # Merged result
        merged = list(dict.fromkeys(all_pcs))
        output.append(f"\n=== Merged Result ({len(merged)} unique) ===")
        output.append(f"PCs (first occurrence): {' '.join(map(str, merged))}")
        # Show constituent parts per part
        for pn in data:
            part_pcs = []
            seen2 = set()
            for bn in data[pn]:
                for pc in data[pn][bn]:
                    if pc not in seen2:
                        part_pcs.append(pc)
                        seen2.add(pc)
            if part_pcs:
                output.append(f"  Constituent [{pn}]: {' '.join(map(str, part_pcs))}")
        if len(merged) > 1:
            c = chord.Chord(sorted(merged))
            output.append(f"Sorted: {' '.join(map(str, sorted(merged)))}")
            output.append(f"Prime: {c.primeFormString}  Forte: {c.forteClass}")

        # Constituents: per-part unique PCs
        part_total = OrderedDict()
        for pn in data:
            all_pn = []
            for bn in data[pn]:
                all_pn.extend(data[pn][bn])
            part_total[pn] = list(dict.fromkeys(all_pn))
        parts_list = []
        for pn in part_total:
            uniq = part_total[pn]
            fc = chord.Chord(uniq).forteClass if len(uniq) > 1 else ""
            label = f"[{' '.join(map(str, uniq))}]({pn})"
            if fc:
                label += f" {fc}"
            parts_list.append(label)
        output.append("Constituents: " + " + ".join(parts_list))

        self._result.setText("\n".join(output))


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
        layout.setContentsMargins(2, 0, 2, 0)
        layout.setSpacing(0)

        # ── Open score button ────────────────────────────────────────
        top_bar = QHBoxLayout()
        self._btn_open = QPushButton(tr("tab.open_score"))
        setup_open_menu(self._btn_open, self, lambda score, path: self._main_window.set_score(score, path))
        top_bar.addWidget(self._btn_open)

        big_font = QFont()
        big_font.setPointSize(13)

        self._btn_row_division = QPushButton(tr("tt.btn_row_division"))
        self._btn_row_division.setFont(big_font)
        self._btn_row_division.setProperty("accent", "teal")
        self._btn_row_division.clicked.connect(self._on_open_row_division)
        top_bar.addWidget(self._btn_row_division)

        self._btn_subset_search = QPushButton(tr("tt.subset_group"))
        self._btn_subset_search.setFont(big_font)
        self._btn_subset_search.setProperty("accent", "teal")
        self._btn_subset_search.clicked.connect(self._on_open_subset_search)
        top_bar.addWidget(self._btn_subset_search)

        self._btn_merge_search = QPushButton(tr("tt.btn_merge_search"))
        self._btn_merge_search.setFont(big_font)
        self._btn_merge_search.setProperty("accent", "teal")
        self._btn_merge_search.clicked.connect(self._on_open_merge_search)
        top_bar.addWidget(self._btn_merge_search)

        self._btn_custom_merge = QPushButton(tr("tt.custom_merge_title"))
        self._btn_custom_merge.setFont(big_font)
        self._btn_custom_merge.setProperty("accent", "teal")
        self._btn_custom_merge.clicked.connect(self._on_open_custom_merge)
        top_bar.addWidget(self._btn_custom_merge)

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
        self._btn_show_row = QPushButton(tr("tt.btn_show_row"))
        self._btn_show_row.pressed.connect(lambda: self._on_show_row())
        self._btn_confirm = QPushButton(tr("tt.btn_confirm"))
        self._btn_confirm.clicked.connect(self._on_confirm_manual)
        manual_row.addWidget(self._btn_show_row)
        manual_row.addWidget(self._btn_confirm)
        extract_layout.addLayout(manual_row)

        layout.addWidget(extract_group)

        # ── Forms display — auto-scale font, scrollable ───────────────
        forms_group = QGroupBox(tr("tt.forms_group"))
        forms_layout = QVBoxLayout(forms_group)
        self._forms_text = QTextEdit()
        self._forms_text.setReadOnly(True)
        self._forms_text.setMinimumHeight(180)
        # Monospace font for forms
        self._forms_font = QFont('Consolas')
        self._forms_font.setPointSize(18)
        self._forms_font.setStyleHint(QFont.Monospace)
        self._forms_text.setFont(self._forms_font)
        self._forms_text.document().setDefaultFont(self._forms_font)
        self._forms_text.setStyleSheet(
            "QTextEdit { background-color: #fefdfb; color: #2c2c2c; }"
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
        matrix_layout.setContentsMargins(0, 0, 0, 0)

        # Hint: A=10, B=11
        hint = QLabel("A = 10    B = 11")
        hint.setAlignment(Qt.AlignRight)
        hint.setStyleSheet("color: #888; font-size: 10pt; padding: 0 6px;")
        matrix_layout.addWidget(hint)

        # Scrollable container for numeric matrix
        matrix_scroll = QScrollArea()
        matrix_scroll.setWidgetResizable(True)
        matrix_scroll.setMaximumHeight(560)
        matrix_scroll.setVerticalScrollBarPolicy(Qt.ScrollBarAlwaysOn)

        self._matrix_numeric = QTextEdit()
        self._matrix_numeric.setReadOnly(True)
        self._matrix_numeric.setMinimumHeight(200)
        self._matrix_numeric.setLineWrapMode(QTextEdit.NoWrap)
        # Monospace font for matrix — fixed 20pt
        _family_str = monospace_font_family().replace('"', '').split(",")[0].strip()
        self._matrix_font_family = _family_str
        self._matrix_font = QFont(_family_str)
        self._matrix_font.setPointSize(20)
        self._matrix_font.setStyleHint(QFont.Monospace)
        self._matrix_numeric.setFont(self._matrix_font)
        self._matrix_numeric.document().setDefaultFont(self._matrix_font)
        self._matrix_numeric.setStyleSheet(
            "QTextEdit {"
            "background-color: #fefdfb;"
            "color: #2c2c2c;"
            "selection-background-color: #d4c8b0;"
            "selection-color: #2c2c2c;"
            "}"
        )
        matrix_scroll.setWidget(self._matrix_numeric)
        matrix_layout.addWidget(matrix_scroll)

        layout.addWidget(matrix_group, 5)

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
        self._btn_show_row.pressed.connect(lambda: self._on_show_row())
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

    def _on_open_row_division(self):
        if not self._row:
            return
        try:
            dlg = RowDivisionDialog(self._row, self)
            dlg.exec_()
        except Exception as e:
            QMessageBox.critical(self, "Error", f"RowDivisionDialog error:\n{type(e).__name__}: {e}")

    def _on_open_subset_search(self):
        if not self._row:
            return
        try:
            dlg = SubsetSearchDialog(self._row, self)
            dlg.exec_()
        except Exception as e:
            QMessageBox.critical(self, "Error", f"SubsetSearchDialog error:\n{type(e).__name__}: {e}")

    def _on_open_custom_merge(self):
        if not self._main_window or not hasattr(self._main_window, '_score') or not self._main_window._score:
            QMessageBox.warning(self, tr("tt.custom_merge_title"), tr("tt.merge_no_score"))
            return
        try:
            dlg = CustomMergeDialog(self._main_window._score, self._main_window, row=self._row)
            dlg.exec_()
        except Exception as e:
            QMessageBox.critical(self, "Error", f"CustomMergeDialog error:\n{type(e).__name__}: {e}")

    def _on_open_merge_search(self):
        if not self._main_window or not hasattr(self._main_window, '_score') or not self._main_window._score:
            QMessageBox.warning(self, tr("tt.merge_title"), tr("tt.merge_no_score"))
            return
        try:
            dlg = MergeSearchDialog(self._main_window._score, self._main_window, row=self._row)
            dlg.exec_()
        except Exception as e:
            QMessageBox.critical(self, "Error", f"MergeSearchDialog error:\n{type(e).__name__}: {e}")

    def _on_panel_toggled(self, visible: bool):
        if visible:
            self._btn_toggle_panel.setText(tr("tt.panel_btn_close"))
        else:
            self._btn_toggle_panel.setText(tr("tt.panel_btn_open"))

    def on_score_loaded(self, score, path: str):
        self._score = score
        # Clear previous analysis results
        self._row = []
        self._last_groups = []
        self._extracted_label.setText("")
        self._manual_input.clear()
        self._forms_text.clear()
        self._row_result.clear()
        self._matrix_widget.setVisible(False)
        self._matrix_numeric.clear()
        # Repopulate part combo
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
            self._btn_show_row.setEnabled(True)
            print("DEBUG: btn enabled", flush=True)
        except ValueError:
            QMessageBox.warning(self, tr("tt.input_error"), tr("tt.input_format_err"))

    def _on_show_row(self):
        if not self._row or len(self._row) != 12:
            return
        try:
            import subprocess, os
            from pathlib import Path
            from src.utils.config import get_musescore_path, get_temp_dir
            from music21 import stream, metadata, note
            s = stream.Score()
            p = stream.Part()
            p.insert(0, metadata.Metadata())
            p.metadata.title = "12-Tone Row"
            m = stream.Measure()
            m.timeSignature = None
            m.leftBarline = None
            m.rightBarline = None
            for pc in self._row:
                n = note.Note()
                n.pitch.midi = pc + 60
                n.quarterLength = 4
                m.append(n)
            p.append(m)
            s.append(p)
            row_name = "_".join(str(p) for p in self._row) + "_twelve-tone_row"
            tmp = os.path.join(get_temp_dir(), row_name + ".musicxml")
            s.write('musicxml', tmp)
            ms = get_musescore_path()
            if ms and os.path.isfile(ms):
                subprocess.Popen([ms, tmp])
            else:
                subprocess.Popen(['open', tmp])
        except Exception as e:
            QMessageBox.critical(self, "Error", str(e))

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
                        temp_default_path("12_tone_matrix_heatmap.png"),
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
            self, tr("tt.export_forms"), get_temp_dir()
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
            self, tr("tt.export_matrix"), temp_default_path("12_tone_matrix_heatmap.png"),
            "PNG (*.png);;All Files (*)"
        )
        if not path:
            return
        self._matrix_widget.fig.savefig(path, dpi=300)
        QMessageBox.information(self, tr("tt.matrix_group"),
                                tr("tt.matrix_exported", path=path))


    def _on_save_row_png(self):
        if not self._last_groups:
            return
        path, _ = QFileDialog.getSaveFileName(
            self, tr("tt.save_row_png"), temp_default_path("row_groups.png"),
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
