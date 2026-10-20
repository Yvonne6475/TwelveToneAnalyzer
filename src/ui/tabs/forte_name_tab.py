"""Forte Name tab: batch pitch-class set analysis with Forte classification."""

from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QTextEdit,
    QPushButton, QTableWidget, QTableWidgetItem, QHeaderView,
    QMessageBox, QFileDialog,
)
from PyQt5.QtCore import Qt

from music21 import chord

from src.utils.i18n import tr, tr_list
from src.utils.config import temp_default_path
from src.core.merge_utils import MergeSelectorDialog


class ForteNameTab(QWidget):
    """Standalone tab for batch pitch-class set Forte analysis."""

    def __init__(self, main_window=None):
        super().__init__()
        self._main_window = main_window
        self._results = []
        self._bar_info = {}
        self._setup_ui()

    def _setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(6, 6, 6, 6)
        layout.setSpacing(8)

        layout.addWidget(QLabel(tr("forte.input_label")))
        self._input_edit = QTextEdit()
        self._input_edit.setPlaceholderText(
            "0 2 4 7 9\n6 8 11 1 4\n6-33A\n4-Z15\n..."
        )
        self._input_edit.setMinimumHeight(100)
        self._input_edit.setLineWrapMode(QTextEdit.NoWrap)
        layout.addWidget(self._input_edit)

        btn_row = QHBoxLayout()
        self._btn_analyze = QPushButton(tr("forte.btn_analyze"))
        self._btn_analyze.setProperty("accent", "teal")
        self._btn_analyze.clicked.connect(self._on_analyze)
        btn_row.addWidget(self._btn_analyze)

        self._btn_copy = QPushButton(tr("forte.btn_copy"))
        self._btn_copy.setEnabled(False)
        self._btn_copy.clicked.connect(self._on_copy)
        btn_row.addWidget(self._btn_copy)

        self._btn_export = QPushButton(tr("forte.btn_export_csv"))
        self._btn_export.setEnabled(False)
        self._btn_export.clicked.connect(self._on_export_csv)
        btn_row.addWidget(self._btn_export)

        self._btn_from_chord = QPushButton(tr("forte.btn_from_chord"))
        self._btn_from_chord.clicked.connect(self._on_from_chord)
        btn_row.addWidget(self._btn_from_chord)

        self._btn_merge = QPushButton(tr("forte.btn_merge"))
        self._btn_merge.clicked.connect(self._on_merge_from_score)
        btn_row.addWidget(self._btn_merge)

        btn_row.addStretch()
        layout.addLayout(btn_row)

        headers = tr_list("forte.table.headers")
        self._table = QTableWidget(0, len(headers))
        self._table.setHorizontalHeaderLabels(headers)
        self._table.setColumnWidth(0, 600)
        self._table.setWordWrap(True)
        self._table.verticalHeader().setSectionResizeMode(QHeaderView.ResizeToContents)
        self._table.setHorizontalScrollMode(QTableWidget.ScrollPerPixel)
        self._table.setEditTriggers(QTableWidget.NoEditTriggers)
        layout.addWidget(self._table, 1)

    def _compute_forms(self, normal):
        """Compute P, I, R, RI forms from a normal-order pitch-class list.
        P = normal order (prime)
        I = (12 - p) % 12  — standard twelve-tone inversion
        R = retrograde (reverse of P)
        RI = retrograde-inversion (reverse of I)
        """
        if not normal:
            return [], [], [], []
        p_form = list(normal)
        i_form = [(12 - p) % 12 for p in p_form]
        r_form = list(reversed(p_form))
        ri_form = list(reversed(i_form))
        return p_form, i_form, r_form, ri_form

    def _compute_intervals(self, normal):
        """Consecutive intervals in normal order (no wrap-around)."""
        if len(normal) < 2:
            return []
        return [normal[i+1] - normal[i] for i in range(len(normal) - 1)]

    def on_score_loaded(self, score=None, path=None):
        """Clear old results and inputs when a new score is loaded."""
        self._input_edit.clear()
        self._results = []
        self._table.setRowCount(0)
        self._btn_copy.setEnabled(False)
        self._btn_export.setEnabled(False)

    def _on_analyze(self):
        text = self._input_edit.toPlainText().strip()
        if not text:
            QMessageBox.warning(self, tr("forte.title"), tr("forte.empty_input"))
            return

        self._btn_analyze.setEnabled(False); self._btn_analyze.repaint()
        from PyQt5.QtWidgets import QApplication; QApplication.processEvents()
        QApplication.setOverrideCursor(Qt.WaitCursor)
        raw_lines = text.splitlines()
        parsed = []
        pending_comments = []
        for raw_line in raw_lines:
            line = raw_line.strip()
            if not line: continue
            if line.startswith('#'):
                pending_comments.append(line)
                continue
            combined = " | ".join(l.lstrip('# ') for l in pending_comments)
            parsed.append((combined, line))
            pending_comments = []
        self._results = []

        for bar_info_line, line in parsed:
            # Support Forte class names like 6-33A, 3-1, 12-1, 6-33B, etc.
            line_stripped = line.strip()
            import re as _re
            forte_match = _re.match(r'^(\d{1,2}-Z?\d{1,3}[AB]?)$', line_stripped)
            if forte_match:
                try:
                    from music21.chord import fromForteClass
                    c_forte = fromForteClass(forte_match.group(1))
                    pcs = list(c_forte.pitchClasses)
                except Exception:
                    pcs = []
            else:
                try:
                    pcs = list(map(int, line.split()))
                except ValueError:
                    continue
            if not pcs:
                continue
            full_comment = ""
            if bar_info_line:
                full_comment = bar_info_line
            c = chord.Chord(pcs)
            normal = list(c.normalOrder)
            intervals = self._compute_intervals(pcs)
            iv = "".join(map(str, c.intervalVector))
            p_form, i_form, r_form, ri_form = self._compute_forms(pcs)
            self._results.append({
                "input": pcs,
                "bar_info": full_comment,
                "normal": normal,
                "intervals": intervals,
                "iv": iv,
                "prime": c.primeFormString,
                "forte": c.forteClass,
                "p_form": p_form,
                "i_form": i_form,
                "r_form": r_form,
                "ri_form": ri_form,
            })

        self._table.setRowCount(len(self._results))
        for row, r in enumerate(self._results):
            display_pc = " ".join(map(str, r["input"]))
            if r.get("bar_info"):
                display_pc = r["bar_info"] + "  " + display_pc
            self._table.setItem(row, 0,
                QTableWidgetItem(display_pc))
            self._table.setItem(row, 1,
                QTableWidgetItem(str(r["normal"])))
            item2 = QTableWidgetItem(" ".join(map(str, r["intervals"])))
            item2.setToolTip(" ".join(map(str, r["intervals"])))
            self._table.setItem(row, 2, item2)
            item3 = QTableWidgetItem(r["iv"])
            item3.setToolTip(r["iv"])
            self._table.setItem(row, 3, item3)
            item4 = QTableWidgetItem(r["prime"])
            item4.setToolTip(r["prime"])
            self._table.setItem(row, 4, item4)
            item5 = QTableWidgetItem(r["forte"])
            item5.setToolTip(r["forte"])
            self._table.setItem(row, 5, item5)
            v6 = "[" + ", ".join(map(str, r["p_form"])) + "]"
            item6 = QTableWidgetItem(v6)
            item6.setToolTip(v6)
            self._table.setItem(row, 6, item6)
            v7 = "[" + ", ".join(map(str, r["i_form"])) + "]"
            item7 = QTableWidgetItem(v7)
            item7.setToolTip(v7)
            self._table.setItem(row, 7, item7)
            v8 = "[" + ", ".join(map(str, r["r_form"])) + "]"
            item8 = QTableWidgetItem(v8)
            item8.setToolTip(v8)
            self._table.setItem(row, 8, item8)
            v9 = "[" + ", ".join(map(str, r["ri_form"])) + "]"
            item9 = QTableWidgetItem(v9)
            item9.setToolTip(v9)
            self._table.setItem(row, 9, item9)

        self._btn_copy.setEnabled(bool(self._results))
        self._btn_export.setEnabled(bool(self._results))
        self._btn_analyze.setEnabled(True); QApplication.restoreOverrideCursor()

    def _on_copy(self):
        lines = ["Input Set\tNormal Order\tIntervals\tInterval Vector\tPrime Form\tForte Class\tP\tI\tR\tRI"]
        for r in self._results:
            lines.append(
                f"{' '.join(map(str, r['input']))}\t"
                f"{r['normal']}\t"
                f"{' '.join(map(str, r['intervals']))}\t"
                f"{r['iv']}\t"
                f"{r['prime']}\t{r['forte']}\t"
                f"{'[' + ', '.join(map(str, r['p_form'])) + ']'}\t"
                f"{'[' + ', '.join(map(str, r['i_form'])) + ']'}\t"
                f"{'[' + ', '.join(map(str, r['r_form'])) + ']'}\t"
                f"{'[' + ', '.join(map(str, r['ri_form'])) + ']'}"
            )
        from PyQt5.QtWidgets import QApplication
        QApplication.clipboard().setText("\n".join(lines))
        QMessageBox.information(self, tr("forte.title"), "Copied to clipboard.")

    def _on_export_csv(self):
        path, _ = QFileDialog.getSaveFileName(
            self, tr("forte.save_csv"), temp_default_path("forte_analysis.csv"),
            "CSV (*.csv);;All Files (*)"
        )
        if not path:
            return
        with open(path, 'w', encoding='utf-8') as f:
            f.write("Chord PCs,Normal Order,Intervals,Interval Vector,Prime Form,Forte Class,P,I,R,RI\n")
            for r in self._results:
                f.write(
                    f'"{" ".join(map(str, r["input"]))}",'
                    f'"{r["normal"]}","{" ".join(map(str, r["intervals"]))}",'
                    f'"{r["iv"]}","{r["prime"]}","{r["forte"]}",'
                    f'"{"[" + ", ".join(map(str, r["p_form"])) + "]"}",'
                    f'"{"[" + ", ".join(map(str, r["i_form"])) + "]"}",'
                    f'"{"[" + ", ".join(map(str, r["r_form"])) + "]"}",'
                    f'"{"[" + ", ".join(map(str, r["ri_form"])) + "]"}"\n'
                )
        QMessageBox.information(self, tr("forte.title"),
                                tr("dialog.saved_to", path=path))

    def _on_from_chord(self):
        """Import pc-sets from the Chord Analysis tab via multi-select dialog."""
        mw = self._main_window
        if not mw:
            return
        self._btn_from_chord.setEnabled(False); self._btn_from_chord.repaint()
        from PyQt5.QtWidgets import QApplication; QApplication.processEvents()
        QApplication.setOverrideCursor(Qt.WaitCursor)
        chord_tab = mw._chord_tab
        if not hasattr(chord_tab, '_results') or not chord_tab._results:
            QMessageBox.information(self, tr("forte.title"),
                                    tr("forte.no_chord_msg"))
            self._btn_from_chord.setEnabled(True)
            QApplication.restoreOverrideCursor()
            return

        from PyQt5.QtWidgets import (QDialog, QListWidget, QDialogButtonBox,
                                     QCheckBox)

        # Use chord_tab's display rows directly (same order as table)
        all_items = []
        if hasattr(chord_tab, '_chord_display_rows') and chord_tab._chord_display_rows:
            for row in chord_tab._chord_display_rows:
                t = row["type"]
                if t == "indiv":
                    all_items.append({"pcs": row["pcs"], "bar": row["bar"],
                        "part": row["part"], "forte": row["forte"], "orig_pcs": row["pcs"],
                        "_type": "indiv", "_offset": row["offset"]})
                elif t == "part_merged":
                    all_items.append({"pcs": row["pcs"], "bar": row["bar"],
                        "part": row["part"], "forte": row["forte"],
                        "_type": "part_merged"})
                elif t == "bar_merged":
                    all_items.append({"pcs": row["pcs"], "bar": row["bar"],
                        "parts": row["part"], "forte": row["forte"],
                        "_type": "bar_merged"})
                elif t == "offset_merged":
                    all_items.append({"pcs": row["pcs"], "bar": row["bar"],
                        "offset": row.get("offset",""), "forte": row["forte"],
                        "offset_pcs": row["part"], "_type": "offset_merged"})
        # Fallback: build from _results
        if not all_items and hasattr(chord_tab, '_results'):
            seen = set()
            for r in chord_tab._results:
                key = tuple(sorted(r.pc_set))
                if key not in seen:
                    seen.add(key)
                    all_items.append({"pcs": r.pc_set, "bar": r.bar,
                        "part": r.part_name, "forte": r.forte_class, "_type": "indiv"})

        self._btn_from_chord.setEnabled(True); QApplication.restoreOverrideCursor()
        dlg = QDialog(self)
        dlg.setWindowTitle(tr("forte.from_chord_title"))
        dlg.setMinimumSize(500, 400)
        dlg.setWindowFlags(dlg.windowFlags() & ~Qt.WindowContextHelpButtonHint)
        layout = QVBoxLayout(dlg)

        # select / deselect all
        chk_all = QCheckBox(tr("forte.select_all"))
        chk_all.setChecked(True)
        layout.addWidget(chk_all)

        lst = QListWidget()
        for idx, item in enumerate(all_items):
            pc_str = " ".join(map(str, item["pcs"]))
            t = item.get("_type", "")
            if t == "indiv":
                part = item.get("part", "")
                label = tr("forte.chord_item", bar=item["bar"],
                           pc=pc_str, forte=item["forte"]) + f" ({part})"
            elif t == "part_merged":
                label = f"[{item['part']} merged] Bar {item['bar']}: [{pc_str}] Forte: {item['forte']}"
            elif t == "bar_merged":
                label = f"[Bar merged] Bar {item['bar']}: [{pc_str}] Forte: {item['forte']}"
            elif t == "offset_merged":
                label = f"[Offset merged] Bar {item['bar']} offset {item.get('offset','')}: [{pc_str}] Forte: {item['forte']} ({item.get('offset_pcs','')})"
            else:
                label = f"Bar {item['bar']}: [{pc_str}] Forte: {item['forte']}"
            lst.addItem(label)
            lst.item(lst.count() - 1).setCheckState(Qt.Checked)
            lst.item(lst.count() - 1).setData(Qt.UserRole, pc_str)
        layout.addWidget(lst, 1)

        chk_all.toggled.connect(
            lambda checked: [lst.item(i).setCheckState(
                Qt.Checked if checked else Qt.Unchecked)
                for i in range(lst.count())])

        buttons = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        buttons.accepted.connect(dlg.accept)
        buttons.rejected.connect(dlg.reject)
        layout.addWidget(buttons)

        if dlg.exec_() != QDialog.Accepted:
            self._btn_from_chord.setEnabled(True)
            QApplication.restoreOverrideCursor()
            return

        selected = []
        for i in range(lst.count()):
            if lst.item(i).checkState() == Qt.Checked:
                label = lst.item(i).text()
                pc_str = lst.item(i).data(Qt.UserRole)
                selected.append(f"# {label}")
                selected.append(pc_str)

        if selected:
            self._input_edit.setText("\n".join(selected))
            from PyQt5.QtWidgets import QApplication; QApplication.processEvents()
        else:
            QMessageBox.information(self, tr("forte.title"), tr("forte.no_chord_msg"))


    def _on_merge_from_score(self):
        """Merge selected parts/bars from the score and analyze."""
        from collections import OrderedDict
        from music21 import chord as m21chord
        from PyQt5.QtWidgets import QDialog
        mw = self._main_window
        if not mw or not hasattr(mw, '_score') or not mw._score:
            QMessageBox.information(self, tr("forte.title"),
                                    tr("forte.no_chord_msg"))
            return
        self._input_edit.clear()
        self._results = []
        self._table.setRowCount(0)
        self._btn_copy.setEnabled(False)
        self._btn_export.setEnabled(False)
        dlg = MergeSelectorDialog(mw._score, self)
        if dlg.exec_() != QDialog.Accepted:
            return
        data, all_pcs, offset_data = dlg.get_result()
        # Build selectable items: bar-merged + per-part
        from music21 import chord as _chord
        bar_items = []
        indiv_items = []
        bar_detail = OrderedDict()
        for pn in data:
            for bn in data[pn]:
                bar_detail.setdefault(bn, {})[pn] = sorted(set(data[pn][bn]))
        part_items = []
        for pn in data:
            all_pn_pcs = set()
            seq_pcs = []
            seen_in_bar = set()
            bars_seen = []
            for bn in data[pn]:
                pcs_orig = data[pn][bn]
                seen_in_bar.clear()
                for pc in pcs_orig:
                    if pc in seen_in_bar: continue
                    seen_in_bar.add(pc)
                    if pc not in all_pn_pcs: seq_pcs.append(pc)
                pcs = sorted(set(pcs_orig))
                all_pn_pcs.update(pcs)
                bars_seen.append(bn)
            if len(bars_seen) > 1 and len(all_pn_pcs) > 1:
                sorted_pcs = sorted(all_pn_pcs)
                part_items.append({"pcs": sorted_pcs, "seq": seq_pcs, "part_name": pn,
                    "bar_start": min(bars_seen), "bar_end": max(bars_seen),
                    "forte": _chord.Chord(sorted_pcs).forteClass})
        offset_items = []
        for (obn, ooff), parts in sorted(offset_data.items(), key=lambda x: (x[0][0], x[0][1])):
            all_pcs_o = set()
            parts_list_o = []
            for pn, pcs in parts.items():
                uniq = list(dict.fromkeys(pcs))
                all_pcs_o.update(uniq)
                parts_list_o.append(f"{pn}[{' '.join(map(str, uniq))}]")
            sorted_pcs = sorted(all_pcs_o)
            if len(sorted_pcs) > 1:
                offset_items.append({"pcs": sorted_pcs, "offset_pcs": " + ".join(parts_list_o),
                    "bar": obn, "offset": ooff, "forte": _chord.Chord(sorted_pcs).forteClass})
        for bn in sorted(bar_detail):
            all_pcs_for_bar = set()
            bar_parts = []
            for pn in bar_detail[bn]:
                pcs = bar_detail[bn][pn]
                orig_pcs = list(dict.fromkeys(data[pn][bn]))
                all_pcs_for_bar.update(pcs)
                bar_parts.append(f"{pn} [{', '.join(map(str, orig_pcs))}]")
                if len(pcs) > 1:
                    indiv_items.append({"pcs": pcs, "orig_pcs": orig_pcs, "bar": bn, "part": f"{pn} [{', '.join(map(str, orig_pcs))}]", "forte": _chord.Chord(pcs).forteClass})
            merged_pcs = sorted(all_pcs_for_bar)
            if len(merged_pcs) > 1:
                parts_str = ", ".join(bar_parts)
                bar_items.append({"pcs": merged_pcs, "bar": bn, "parts": parts_str, "forte": _chord.Chord(merged_pcs).forteClass})
        all_items = list(part_items)
        for bn in sorted(bar_detail):
            for _it in indiv_items:
                if _it["bar"] == bn:
                    all_items.append(_it)
            for _it in bar_items:
                if _it["bar"] == bn:
                    all_items.append(_it)
            for _it in offset_items:
                if _it["bar"] == bn:
                    all_items.append(_it)
        # --- Selection dialog (same as Get from chords) ---
        from PyQt5.QtWidgets import (QDialog as _QDialog, QVBoxLayout as _QVBox,
            QListWidget as _QList, QCheckBox as _QCheckBox, QDialogButtonBox as _QBtnBox)
        from PyQt5.QtCore import Qt as _Qt
        _dlg = _QDialog(self)
        _dlg.setWindowTitle(tr("forte.from_chord_title"))
        _dlg.setMinimumSize(500, 400)
        _layout = _QVBox(_dlg)
        _chk_all = _QCheckBox(tr("forte.select_all"))
        _chk_all.setChecked(True)
        _layout.addWidget(_chk_all)
        _lst = _QList()
        for _idx, _item in enumerate(all_items):
            _pc_str = " ".join(map(str, _item["pcs"]))
            if 'part_name' in _item:
                _seq_str = " ".join(map(str, _item.get('seq', _item['pcs'])))
                _label = f"[Part Merge] {_item['part_name']} (Bars {_item['bar_start']}-{_item['bar_end']}): [{_seq_str}] Forte: {_item['forte']}"
            elif 'parts' in _item:
                _disp_pc = " ".join(map(str, _item.get('orig_seq', _item['pcs'])))
                _label = tr("forte.bar_merge_item", bar=_item["bar"], pc=_disp_pc, forte=_item["forte"])
                _label += f" ({_item.get('parts','')})"
            elif 'offset' in _item:
                _label = f"[Offset Merge] Bar {_item['bar']} offset {_item['offset']}: [{_pc_str}] Forte: {_item['forte']} ({_item['offset_pcs']})"
            else:
                _chord_pc = " ".join(map(str, _item.get('orig_pcs', _item['pcs'])))
                _label = tr("forte.chord_item", bar=_item["bar"], pc=_chord_pc, forte=_item["forte"])
                _label += f" ({_item.get('part','')})"
            _lst.addItem(_label)
            _lst.item(_lst.count() - 1).setCheckState(_Qt.Checked)
            _lst.item(_lst.count() - 1).setData(_Qt.UserRole, _pc_str)
        _layout.addWidget(_lst, 1)
        _chk_all.toggled.connect(lambda c: [_lst.item(i).setCheckState(_Qt.Checked if c else _Qt.Unchecked) for i in range(_lst.count())])
        _buttons = _QBtnBox(_QBtnBox.Ok | _QBtnBox.Cancel)
        _buttons.accepted.connect(_dlg.accept)
        _buttons.rejected.connect(_dlg.reject)
        _layout.addWidget(_buttons)
        if _dlg.exec_() != _QDialog.Accepted:
            return
        _selected = []
        for i in range(_lst.count()):
            if _lst.item(i).checkState() == _Qt.Checked:
                _selected.append(_lst.item(i).data(_Qt.UserRole))
        if _selected:
            sel_set = set(_selected); out = []
            for _it in part_items:
                _pk = " ".join(map(str, _it["pcs"]))
                _s = " ".join(map(str, _it.get('seq', _it['pcs'])))
                if _pk in sel_set:
                    out.append(f"# [Part Merge] {_it['part_name']} (Bars {_it['bar_start']}-{_it['bar_end']}): [{_pk}] Forte: {_it['forte']}")
                    out.append(f"# Constituents: [{_s}]({_it['part_name']})")
                    out.append(_s)
                    key = tuple(_it["pcs"])
                    if key not in self._bar_info: self._bar_info[key] = f"{_it['part_name']} (Bars {_it['bar_start']}-{_it['bar_end']})"
            for _it in bar_items:
                _pk = " ".join(map(str, _it["pcs"]))
                _s = " ".join(map(str, _it.get('orig_seq', _it["pcs"])))
                if _pk in sel_set:
                    out.append(f"# [Bar Merge] Bar {_it['bar']}: [{_s}] Forte: {_it['forte']} ({_it.get('parts','')})")
                    out.append(_s)
            for _it in indiv_items:
                _pk = " ".join(map(str, _it["pcs"]))
                _s = " ".join(map(str, _it.get('orig_pcs', _it["pcs"])))
                if _pk in sel_set:
                    out.append(f"# [Chord] Bar {_it['bar']}: [{_s}] Forte: {_it['forte']} ({_it.get('part','')})")
                    out.append(_s)
            if not out:
                out = list(_selected)
            self._input_edit.setText("\n".join(out))
