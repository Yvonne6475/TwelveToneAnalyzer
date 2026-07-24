"""Set Relations tab: subset, complement, Z-relation, K-relation, complex, nexus."""

from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QGroupBox, QLabel,
    QTextEdit, QComboBox, QPushButton, QScrollArea,
    QMessageBox, QApplication, QDialog, QListWidget,
    QDialogButtonBox, QAbstractItemView,
)
from PyQt5.QtCore import Qt, QThread, pyqtSignal, QObject
from PyQt5.QtGui import QFontMetrics

from music21 import chord

from src.core.set_relations import (
    complement, interval_vector,
    subset_superset_relations, z_relations, k_relations,
    invariant_containments, set_complex_around, nexus_set,
    is_tn_or_tni_equivalent, _precompute_iv,
)
from src.utils.i18n import tr

from src.core.merge_utils import MergeSelectorDialog, select_merge_items

def _pc_str(pcs) -> str:
    return " ".join(map(str, pcs))


def _pc_bracket(pcs) -> str:
    return "[" + ", ".join(map(str, pcs)) + "]"


def _forte(pcs) -> str:
    return chord.Chord(pcs).forteClass


def _transpose(pcs: list[int], n: int) -> list[int]:
    """T_n transposition: (p + n) mod 12."""
    return [(p + n) % 12 for p in pcs]


def _compute_forms(normal):
    """Compute P, I, R, RI from normal-order pitch-class list.
    I(p) = (12 - p) % 12  — standard twelve-tone inversion.
    """
    if not normal:
        return [], [], [], []
    p_form = list(normal)
    i_form = [(12 - p) % 12 for p in p_form]
    r_form = list(reversed(p_form))
    ri_form = list(reversed(i_form))
    return p_form, i_form, r_form, ri_form


class _AnalysisWorker(QObject):
    """Runs set-relations computation in a background thread."""
    progress = pyqtSignal(int, int)
    analysis_ready = pyqtSignal(dict)
    nexus_ready = pyqtSignal(dict)
    error = pyqtSignal(str)

    def __init__(self):
        super().__init__()
        self._cancelled = False

    def cancel(self):
        self._cancelled = True

    def do_analyze(self, target: list, universe: list):
        """Compute set_complex_around for a single target."""
        try:
            if self._cancelled:
                return
            iv_cache = _precompute_iv(universe)
            if self._cancelled:
                return
            cpx = set_complex_around(target, universe, iv_cache)
            if not self._cancelled:
                self.analysis_ready.emit(cpx)
        except Exception as e:
            self.error.emit(str(e))

    def do_nexus(self, universe: list):
        """Compute nexus_set over the entire universe."""
        try:
            total = len(universe)
            def _progress(idx, t):
                if self._cancelled:
                    return
                self.progress.emit(idx, t)
            result = nexus_set(universe, progress_callback=_progress)
            if not self._cancelled:
                self.nexus_ready.emit(result)
        except Exception as e:
            self.error.emit(str(e))


class SetRelationsTab(QWidget):
    def __init__(self, main_window=None):
        super().__init__()
        self._main_window = main_window
        self._universe = []
        self._bar_info = {}
        self._merged_sets = set()  # tuple(sorted(pcs)) -> bar_number (or range str)
        self._merged_constituents = {}
        self._worker = None
        self._thread = None
        self._setup_ui()

    def _setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(6, 6, 6, 6)
        layout.setSpacing(8)

        # ── Universe input ──
        univ_group = QGroupBox(tr("sr.universe_group"))
        univ_layout = QVBoxLayout(univ_group)
        univ_layout.addWidget(QLabel(tr("sr.universe_label")))
        self._universe_edit = QTextEdit()
        self._universe_edit.setPlaceholderText(
            "6 8 11 1 4\n7 10 0 3 5\n2 5 7 9 0\n7 9 0\n6 3 8 11\n"
            "0 7 2 9\n4 11 2 9\n0 7 5 2\n0 1 5 10\n0 7 2 10"
        )
        self._universe_edit.setMinimumHeight(80)
        self._universe_edit.setMaximumHeight(120)
        univ_layout.addWidget(self._universe_edit)
        layout.addWidget(univ_group)

        # ── Status label ──
        self._status_label = QLabel("")
        self._status_label.setStyleSheet("color: #856404; font-weight: bold;")
        self._status_label.setVisible(False)
        layout.addWidget(self._status_label)

        # ── Target & action ──
        target_row = QHBoxLayout()
        target_row.addWidget(QLabel(tr("sr.target_label")))
        self._target_combo = QComboBox()
        self._target_combo.setMinimumWidth(260)
        self._target_combo.setMaxVisibleItems(30)
        self._target_combo.setSizeAdjustPolicy(QComboBox.AdjustToContents)
        _tv = self._target_combo.view()
        _tv.setHorizontalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        _tv.setVerticalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        _tv.setMinimumWidth(800)
        self._target_combo.currentIndexChanged.connect(self._on_target_changed)
        target_row.addWidget(self._target_combo, 1)

        self._btn_analyze = QPushButton(tr("sr.btn_analyze"))
        self._btn_analyze.setProperty("accent", "teal")
        self._btn_analyze.clicked.connect(self._on_analyze)
        target_row.addWidget(self._btn_analyze)

        self._btn_nexus = QPushButton(tr("sr.btn_nexus"))
        self._btn_nexus.setProperty("accent", "purple")
        self._btn_nexus.clicked.connect(self._on_nexus)
        target_row.addWidget(self._btn_nexus)

        self._btn_from_chord = QPushButton(tr("sr.btn_from_chord"))
        self._btn_from_chord.clicked.connect(self._on_from_chord)
        target_row.addWidget(self._btn_from_chord)
        self._btn_merge = QPushButton(tr("forte.btn_merge"))
        self._btn_merge.clicked.connect(self._on_merge_from_score)
        target_row.addWidget(self._btn_merge)
        layout.addLayout(target_row)

        # ── Results (scrollable) ──
        self._results_widget = QWidget()
        self._results_layout = QVBoxLayout(self._results_widget)
        self._results_layout.setContentsMargins(0, 0, 0, 0)
        self._results_layout.setSpacing(6)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        scroll.setWidget(self._results_widget)
        layout.addWidget(scroll, 1)

    def on_score_loaded(self, score=None, path=None):
        """Clear old chord-derived data when a new score is loaded."""
        self._universe = []
        self._universe_edit.clear()
        self._target_combo.clear()
        self._clear_results()

    def _ensure_thread(self):
        """Create a fresh thread + worker if needed (one-shot)."""
        if self._thread is not None:
            return  # Still running
        self._thread = QThread(self)
        self._worker = _AnalysisWorker()
        self._worker.moveToThread(self._thread)
        self._worker.analysis_ready.connect(self._on_analysis_done)
        self._worker.nexus_ready.connect(self._on_nexus_done)
        self._worker.error.connect(self._on_worker_error)
        self._worker.progress.connect(self._on_progress)
        self._thread.started.connect(lambda: None)  # placeholder
        self._thread.start()

    def _cleanup_thread(self):
        """Cancel any running worker, quit the thread, and disconnect signals."""
        if self._thread is not None:
            if self._worker is not None:
                self._worker.cancel()
                try:
                    self._worker.analysis_ready.disconnect(self._on_analysis_done)
                    self._worker.nexus_ready.disconnect(self._on_nexus_done)
                    self._worker.error.disconnect(self._on_worker_error)
                    self._worker.progress.disconnect(self._on_progress)
                except TypeError:
                    pass  # Already disconnected
            self._thread.quit()
            if not self._thread.wait(3000):
                self._thread.terminate()
            self._thread.deleteLater()
            self._worker.deleteLater()
        self._thread = None
        self._worker = None

    def _set_busy(self, busy: bool):
        self._btn_analyze.setEnabled(not busy)
        self._btn_nexus.setEnabled(not busy)
        self._btn_from_chord.setEnabled(not busy)
        self._universe_edit.setEnabled(not busy)
        self._target_combo.setEnabled(not busy)
        self._status_label.setVisible(busy)
        if busy:
            self._status_label.setText(tr("sr.computing"))
            QApplication.setOverrideCursor(Qt.WaitCursor)
        else:
            QApplication.restoreOverrideCursor()

    def _parse_universe(self):
        text = self._universe_edit.toPlainText().strip()
        lines = [l.strip() for l in text.splitlines() if l.strip() and not l.strip().startswith('#')]
        universe = []
        for line in lines:
            try:
                pcs = list(map(int, line.split()))
            except ValueError:
                continue
            if pcs:
                universe.append(pcs)
        return universe

    def _on_analyze(self):
        self._universe = self._parse_universe()
        if not self._universe:
            QMessageBox.warning(self, tr("sr.title"), tr("sr.empty_universe"))
            return
        self._sync_combo_from_universe()

        pc_str = self._target_combo.currentData()
        if not pc_str:
            QMessageBox.warning(self, tr("sr.title"), tr("sr.empty_target"))
            return
        try:
            target = list(map(int, pc_str.split()))
        except ValueError:
            QMessageBox.warning(self, tr("sr.title"), tr("sr.invalid_target"))
            return

        self._cleanup_thread()
        self._ensure_thread()
        self._set_busy(True)
        self._worker.do_analyze(target, self._universe)

    def _on_nexus(self):
        self._universe = self._parse_universe()
        if len(self._universe) < 2:
            QMessageBox.warning(self, tr("sr.title"), tr("sr.need_more_sets"))
            return
        self._sync_combo_from_universe()

        self._cleanup_thread()
        self._ensure_thread()
        self._set_busy(True)
        self._worker.do_nexus(self._universe)

    def _on_analysis_done(self, cpx: dict):
        self._set_busy(False)
        self._display_complex(cpx)

    def _on_nexus_done(self, result: dict):
        self._set_busy(False)
        candidates = result["nexus_candidates"]
        complexes = result["complexes"]
        score = result["score"]
        self._clear_results()

        # ── Dedicated nexus dialog (avoids combo-clash + shows score) ──
        dlg = QDialog(self)
        dlg.setWindowTitle(tr("sr.nexus_dialog_title"))
        dlg.resize(520, 280)
        dlg_layout = QVBoxLayout(dlg)

        dlg_layout.addWidget(QLabel(
            tr("sr.nexus_dialog_header", count=len(candidates), score=score)))

        lst = QListWidget()
        lst.setSelectionMode(QAbstractItemView.SingleSelection)
        for i, nexus in enumerate(candidates):
            nexus_str = _pc_str(nexus)
            label = tr("sr.nexus_item", pc=nexus_str, forte=_forte(nexus), score=score)
            lst.addItem(label)
            lst.item(lst.count() - 1).setData(Qt.UserRole, i)
        lst.setCurrentRow(0)
        dlg_layout.addWidget(lst)

        btns = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        btns.accepted.connect(dlg.accept)
        btns.rejected.connect(dlg.reject)
        dlg_layout.addWidget(btns)

        if dlg.exec_() != QDialog.Accepted:
            return

        # User picked a nexus → select in combo + directly display analysis
        selected = lst.currentItem()
        if selected is None:
            return
        i = selected.data(Qt.UserRole)
        nexus = candidates[i]
        nexus_str = _pc_str(nexus)

        idx = self._target_combo.findData(nexus_str)
        if idx < 0:
            self._target_combo.blockSignals(True)
            self._target_combo.insertItem(0,
                tr("sr.nexus_item", pc=nexus_str, forte=_forte(nexus), score=score),
                nexus_str)
            self._target_combo.setCurrentIndex(0)
            self._target_combo.blockSignals(False)
        else:
            self._target_combo.setCurrentIndex(idx)

        self._display_complex(complexes[i], nexus_info=result)

    def _on_worker_error(self, msg: str):
        self._set_busy(False)
        QMessageBox.critical(self, tr("sr.title"), msg)

    def _on_progress(self, idx: int, total: int):
        self._status_label.setText(tr("sr.progress", current=idx + 1, total=total))

    def _on_from_chord(self):
        """Import pc-sets from the chord analysis tab into the universe."""
        mw = self._main_window
        if not mw:
            return
        chord_tab = mw._chord_tab
        if not hasattr(chord_tab, '_results') or not chord_tab._results:
            QMessageBox.information(self, tr("sr.title"),
                                    tr("sr.no_chord_msg"))
            return

        self._btn_from_chord.setEnabled(False); self._btn_from_chord.repaint()
        from PyQt5.QtWidgets import QApplication; QApplication.processEvents()
        QApplication.setOverrideCursor(Qt.WaitCursor)
        results = chord_tab._results

        # 1) Merge by bar
        bar_sets = {}
        bar_set_bars = {}
        for r in results:
            if len(r.pc_set) <= 1:
                continue
            bar_sets.setdefault(r.bar, set()).update(r.pc_set)
            bar_set_bars.setdefault(r.bar, []).append(r.bar)
        self._merged_sets = set()
        self._merged_constituents = {}
        # Track per-bar constituents
        bar_constituents = {}
        for r in results:
            if len(r.pc_set) <= 1:
                continue
            bar_constituents.setdefault(r.bar, []).append((list(r.pc_set), r.part_name))
        bar_lines = []
        for bar in sorted(bar_sets):
            pc = sorted(bar_sets[bar])
            if pc:
                bar_lines.append(_pc_str(pc))
                key = tuple(sorted(pc))
                self._bar_info[key] = f"Bar {bar}"
                self._merged_sets.add(key)
                cons = bar_constituents.get(bar, [])
                if key not in self._merged_constituents:
                    self._merged_constituents[key] = set()
                for pcs, part in cons:
                    self._merged_constituents[key].add((tuple(pcs), part))

        # 2) Individual items (dedup for display, but accumulate bar info)
        indiv_lines = []
        seen = set()
        for r in results:
            key = tuple(sorted(r.pc_set))
            if key not in seen:
                seen.add(key)
                indiv_lines.append(_pc_str(r.pc_set))
            if key not in self._bar_info:
                self._bar_info[key] = f"Bar {r.bar} ({r.part_name})"
            else:
                existing = self._bar_info[key]
                entry = f"Bar {r.bar} ({r.part_name})"
                if entry not in existing:
                    self._bar_info[key] = existing + f"; {entry}"
        all_lines = bar_lines + indiv_lines

        self._universe_edit.setText("\n".join(all_lines))

        # Populate combo: bar-merged first (with "Bar" prefix), then individual (with Forte name)
        self._target_combo.blockSignals(True)
        self._target_combo.clear()
        for bar in sorted(bar_sets):
            pc = sorted(bar_sets[bar])
            if pc:
                key = tuple(sorted(pc))
                cons = self._merged_constituents.get(key, set())
                extra = ""
                if cons:
                    parts = []
                    for pcs, part in sorted(cons, key=lambda x: (tuple(x[0]), x[1])):
                        parts.append(f"[{' '.join(map(str, pcs))}]({part})")
                    extra = "  ← from " + " + ".join(parts)
                label = tr("sr.combo_bar", bar=bar, pc=_pc_str(pc), forte=_forte(pc)) + extra
                self._target_combo.addItem(label, _pc_str(pc))
        seen_combo = set()
        for r in results:
            if len(r.pc_set) <= 1:
                continue
            key = tuple(sorted(r.pc_set))
            if key in seen_combo:
                continue
            seen_combo.add(key)
            bar_str = self._bar_info.get(key, f"Bar {r.bar}")
            label = tr("sr.combo_item", pc=_pc_str(r.pc_set), forte=_forte(r.pc_set)) + f" ({bar_str})"
            self._target_combo.addItem(label, _pc_str(r.pc_set))
        self._target_combo.blockSignals(False)

        if all_lines:
            self._target_combo.setCurrentIndex(0)

        self._adjust_combo_dropdown_width()
        self._btn_from_chord.setEnabled(True); QApplication.restoreOverrideCursor()

    def _on_target_changed(self, index):
        pass

    def _adjust_combo_dropdown_width(self):
        from PyQt5.QtWidgets import QApplication
        screen_w = QApplication.primaryScreen().availableSize().width() if QApplication.primaryScreen() else 1200
        fm = self._target_combo.fontMetrics()
        max_w = 0
        for i in range(self._target_combo.count()):
            max_w = max(max_w, fm.boundingRect(self._target_combo.itemText(i)).width())
        view = self._target_combo.view()
        if view:
            view.setMinimumWidth(min(max_w + 60, screen_w - 100))
            view.setHorizontalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        # Set tooltip for full text on each item
        for i in range(self._target_combo.count()):
            self._target_combo.setItemData(i, self._target_combo.itemText(i), Qt.ToolTipRole)

    def _sync_combo_from_universe(self):
        self._target_combo.blockSignals(True)
        for s in self._universe:
            pc_str = _pc_str(s)
            if self._target_combo.findData(pc_str) >= 0:
                continue
            key = tuple(sorted(s))
            if key in self._merged_sets:
                bar_info = self._bar_info.get(key, "")
                label = f"[Merged] {bar_info}: {pc_str}  Forte: {_forte(s)}"
            else:
                bar_str = self._bar_info.get(key, "")
                if bar_str:
                    label = f"{bar_str}: {pc_str}  Forte: {_forte(s)}"
                else:
                    label = tr("sr.combo_item", pc=pc_str, forte=_forte(s))
            self._target_combo.addItem(label, pc_str)
        self._target_combo.blockSignals(False)
        self._adjust_combo_dropdown_width()

    def _clear_results(self):
        while self._results_layout.count():
            item = self._results_layout.takeAt(0)
            if item.widget():
                w = item.widget()
                w.setParent(None)
                w.deleteLater()
        # Also clear any spacers
        self._results_layout.update()

    def _add_section(self, title: str, items: list[str]):
        group = QGroupBox(title)
        gl = QVBoxLayout(group)
        if not items:
            lbl = QLabel(tr("sr.none"))
            lbl.setTextInteractionFlags(Qt.TextSelectableByMouse)
            gl.addWidget(lbl)
        else:
            numbered = [f"{i+1}. {item}" for i, item in enumerate(items)]
            edit = QTextEdit()
            edit.setReadOnly(True)
            edit.setPlainText("\n".join(numbered))
            edit.setHorizontalScrollBarPolicy(Qt.ScrollBarAsNeeded)
            edit.setVerticalScrollBarPolicy(Qt.ScrollBarAsNeeded)
            edit.setMinimumHeight(min(len(items) * 25 + 10, 300))
            gl.addWidget(edit)
        self._results_layout.addWidget(group)

    def _on_merge_from_score(self):
        """Merge from score and load selected sets into universe."""
        from src.core.merge_utils import MergeSelectorDialog, select_merge_items
        from collections import OrderedDict
        from music21 import chord as _chord
        from PyQt5.QtWidgets import QDialog
        mw = getattr(self, '_main_window', None)
        if not mw or not hasattr(mw, '_score') or not mw._score:
            QMessageBox.information(self, tr("forte.title"), tr("forte.no_chord_msg"))
            return
        self._universe_edit.clear()
        self._clear_results()
        self._target_combo.clear()
        self._universe = []
        dlg = MergeSelectorDialog(mw._score, self)
        if dlg.exec_() != QDialog.Accepted:
            return
        data, all_pcs = dlg.get_result()
        bar_detail = OrderedDict()
        for pn in data:
            for bn in data[pn]:
                bar_detail.setdefault(bn, {})[pn] = sorted(set(data[pn][bn]))
        part_items = []
        for pn in data:
            all_pn_pcs = set(); seq_pcs = []; seen_in_bar = set(); bars_seen = []
            for bn in data[pn]:
                pcs_orig = data[pn][bn]; seen_in_bar.clear()
                for pc in pcs_orig:
                    if pc in seen_in_bar: continue
                    seen_in_bar.add(pc)
                    if pc not in all_pn_pcs: seq_pcs.append(pc)
                pcs = sorted(set(pcs_orig)); all_pn_pcs.update(pcs); bars_seen.append(bn)
            if len(bars_seen) > 1 and len(all_pn_pcs) > 1:
                sp = sorted(all_pn_pcs)
                part_items.append({"pcs": sp, "seq": seq_pcs, "part_name": pn,
                    "bar_start": min(bars_seen), "bar_end": max(bars_seen),
                    "forte": _chord.Chord(sp).forteClass})
        bar_items, indiv_items = [], []
        for bn in sorted(bar_detail):
            all_pb = set()
            for pn in bar_detail[bn]:
                pcs = bar_detail[bn][pn]; orig_pcs = list(dict.fromkeys(data[pn][bn])); all_pb.update(pcs)
                if len(pcs) > 1:
                    indiv_items.append({"pcs": pcs, "orig_pcs": orig_pcs, "bar": bn, "part": f"{pn} [{', '.join(map(str, orig_pcs))}]", "forte": _chord.Chord(pcs).forteClass})
            merged = sorted(all_pb)
            if len(merged) > 1:
                bar_items.append({"pcs": merged, "bar": bn, "parts": ", ".join(f"{pn} [{', '.join(map(str, bar_detail[bn][pn]))}]" for pn in bar_detail[bn]), "forte": _chord.Chord(merged).forteClass})
        sel = select_merge_items(self, part_items + bar_items + indiv_items, bar_items)
        if sel:
            sel_set = set(sel); out_lines = []
            import re as _re
            def _parse_cons(ps):
                res = []
                for seg in ps.split('], '):
                    seg = seg.strip()
                    if ' [' not in seg: continue
                    nm, ps2 = seg.split(' [', 1); ps2 = ps2.rstrip(']')
                    res.append((tuple(map(int, ps2.split(', '))), nm))
                return res
            for _it in part_items:
                _pk = " ".join(map(str, _it["pcs"])); _s = " ".join(map(str, _it.get('seq', _it['pcs'])))
                if _pk in sel_set:
                    out_lines.append(f"# [Part Merge] {_it['part_name']} (Bars {_it['bar_start']}-{_it['bar_end']}): [{_pk}] Forte: {_it['forte']}")
                    out_lines.append(f"# Constituents: [{_s}]({_it['part_name']})")
                    out_lines.append(_s)
                    key = tuple(_it["pcs"])
                    self._merged_sets.add(key)
                    self._bar_info[key] = f"{_it['part_name']} (Bars {_it['bar_start']}-{_it['bar_end']})"
                    if key not in self._merged_constituents: self._merged_constituents[key] = set()
                    self._merged_constituents[key].add((tuple(_it.get('seq', _it['pcs'])), _it['part_name']))
            for _it in bar_items:
                _pk = " ".join(map(str, _it["pcs"])); _s = " ".join(map(str, _it.get('orig_seq', _it["pcs"])))
                if _pk in sel_set:
                    out_lines.append(f"# [Bar Merge] Bar {_it['bar']}: [{_s}] Forte: {_it['forte']} ({_it.get('parts','')})")
                    out_lines.append(_s)
                    key = tuple(_it["pcs"])
                    self._merged_sets.add(key)
                    self._bar_info[key] = f"Bar {_it['bar']}"
                    if key not in self._merged_constituents: self._merged_constituents[key] = set()
                    for cons_pcs, cons_part in _parse_cons(_it.get('parts', '')):
                        self._merged_constituents[key].add((cons_pcs, cons_part))
            for _it in indiv_items:
                _pk = " ".join(map(str, _it["pcs"])); _s = " ".join(map(str, _it.get('orig_pcs', _it["pcs"])))
                if _pk in sel_set:
                    out_lines.append(f"# [Chord] Bar {_it['bar']}: [{_s}] Forte: {_it['forte']} ({_it.get('part','')})")
                    out_lines.append(_s)
                    key = tuple(_it["pcs"])
                    entry = f"Bar {_it['bar']} ({_it.get('part','')})"
                    if key not in self._bar_info: self._bar_info[key] = entry
                    elif entry not in self._bar_info[key]: self._bar_info[key] += f"; {entry}"
            if not out_lines:
                out_lines = list(sel)
            cur = self._universe_edit.toPlainText().strip()
            self._universe_edit.setText("\n".join(out_lines))
            self._target_combo.clear()
            self._universe = self._parse_universe()
            if self._universe:
                self._target_combo.blockSignals(True)
                pending_comments = ""
                for line in out_lines:
                    if line.startswith('#'):
                        pending_comments = (pending_comments + line + "  ").strip()
                    else:
                        pc_str = line
                        label = (pending_comments + "  " + pc_str).strip() if pending_comments else pc_str
                        self._target_combo.addItem(label, pc_str)
                        pending_comments = ""
                self._target_combo.blockSignals(False)

    def _display_complex(self, cpx, nexus_info=None):
        self._clear_results()

        target = cpx["target"]
        comp = cpx["complement"]
        iv = cpx["interval_vector"]

        # Deduplicate and filter out single-note sets from result sections
        for key in ["subsets", "supersets", "z_related", "k_related", "invariants"]:
            seen = set()
            deduped = []
            for s in cpx[key]:
                if len(s) <= 1:
                    continue
                t = tuple(sorted(s))
                if t not in seen:
                    seen.add(t)
                    deduped.append(s)
            cpx[key] = deduped

        # Precompute all Forte names and IVs to avoid redundant chord.Chord() calls
        all_sets = [target, comp] + cpx["subsets"] + cpx["supersets"] + \
                   cpx["z_related"] + cpx["k_related"] + cpx["invariants"]
        forte_cache = {}
        iv_cache_all = {}
        prime_cache = {}
        intervals_cache = {}
        normal_cache = {}
        for s in all_sets:
            t = tuple(sorted(s))
            if t not in forte_cache:
                forte_cache[t] = _forte(s)
                iv_cache_all[t] = str(interval_vector(s))
                c = chord.Chord(s)
                prime_cache[t] = c.primeFormString
                normal_cache[t] = str(list(c.normalOrder))
                # Intervals from Chords PCs order (consecutive differences, mod 12)
                intv = [(s[i+1] - s[i]) % 12 for i in range(len(s) - 1)] if len(s) >= 2 else []
                intervals_cache[t] = " ".join(map(str, intv))

        def _fmt(s):
            t = tuple(sorted(s))
            prefix = ""
            if t in self._merged_sets:
                bar_info = self._bar_info.get(t, "")
                import re as _re
                bars = sorted(set(_re.findall(r'Bar\s+\d+', bar_info)))
                bar_label = ", ".join(bars) if bars else bar_info
                prefix = f"[Merged] {bar_label}: [{_pc_str(s)}] Forte: {forte_cache[t]}"
            else:
                bar_str = self._bar_info.get(t, "")
                if bar_str: prefix = f"{bar_str}: [{_pc_str(s)}] Forte: {forte_cache[t]}"
            if prefix:
                return (prefix + "  Intervals: " + intervals_cache[t] +
                    "  Normal: " + normal_cache[t] +
                    "  Prime: " + prime_cache[t] +
                    "  IV: " + iv_cache_all[t])
            return tr("sr.rel_item", pc=_pc_str(s),
                forte=forte_cache[t], iv=iv_cache_all[t],
                prime=prime_cache[t], intervals=intervals_cache[t],
                normal=normal_cache[t])

        # Basic info
        info_group = QGroupBox(tr("sr.info_group"))
        info_layout = QVBoxLayout(info_group)
        target_txt = self._target_combo.currentText() if self._target_combo.count() > 0 else _pc_str(target)
        target_edit = QTextEdit()
        target_edit.setReadOnly(True)
        target_edit.setPlainText(target_txt + "\n" + _fmt(target).split("  Intervals:", 1)[-1].strip() if "  Intervals:" in _fmt(target) else target_txt)
        info_layout.addWidget(target_edit)
        normal = list(chord.Chord(target).normalOrder)
        intervals = [normal[i+1] - normal[i] for i in range(len(normal) - 1)] if len(normal) >= 2 else []
        lbl_intervals = QLabel(
            tr("sr.info_intervals", pc=_pc_str(normal),
               intervals=" ".join(map(str, intervals))))
        lbl_intervals.setTextInteractionFlags(Qt.TextSelectableByMouse)
        info_layout.addWidget(lbl_intervals)

        if nexus_info:
            candidates = nexus_info.get("nexus_candidates", [nexus_info.get("nexus")])
            nexus_label = ", ".join(_pc_str(c) for c in candidates)
            lbl_nexus = QLabel(
                tr("sr.info_nexus", pc=nexus_label, score=nexus_info["score"]))
            lbl_nexus.setTextInteractionFlags(Qt.TextSelectableByMouse)
            info_layout.addWidget(lbl_nexus)
        self._results_layout.addWidget(info_group)

        # Relationships
        self._add_section(
            tr("sr.subsets", n=len(cpx["subsets"])),
            [_fmt(s) for s in cpx["subsets"]])

        self._add_section(
            tr("sr.supersets", n=len(cpx["supersets"])),
            [_fmt(s) for s in cpx["supersets"]])

        self._add_section(
            tr("sr.z_related", n=len(cpx["z_related"])),
            [_fmt(s) for s in cpx["z_related"]])

        self._add_section(
            tr("sr.k_related", n=len(cpx["k_related"])),
            [_fmt(s) for s in cpx["k_related"]])

        self._add_section(
            tr("sr.invariants", n=len(cpx["invariants"])),
            [_fmt(s) for s in cpx["invariants"]])

        # ── P / I / R / RI transformational matches ──
        self._add_transformation_section(cpx)

        self._results_layout.addStretch()
        self._results_widget.setMinimumWidth(2000)

    def _add_transformation_section(self, cpx):
        """Search the universe for T_n, P, I, R, RI matches of the target."""
        target = cpx["target"]
        p_form, i_form, r_form, ri_form = _compute_forms(target)

        p_matches, i_matches, r_matches, ri_matches = [], [], [], []
        tn_matches = {}
        for s in self._universe:
            if s == p_form and s != target:
                p_matches.append(s)
            if s == i_form:
                i_matches.append(s)
            if s == r_form:
                r_matches.append(s)
            if s == ri_form:
                ri_matches.append(s)
            for n in range(12):
                if n == 0 and s == target:
                    continue
                if s == _transpose(target, n):
                    tn_matches.setdefault(n, []).append(s)
        # Dedup
        for n in tn_matches:
            seen = set(); uniq = []
            for ms in tn_matches[n]:
                t = tuple(ms)
                if t not in seen: seen.add(t); uniq.append(ms)
            tn_matches[n] = uniq
        for lst in [p_matches, i_matches, r_matches, ri_matches]:
            seen = set(); deduped = []
            for ms in lst:
                t = tuple(ms)
                if t not in seen: seen.add(t); deduped.append(ms)
            lst[:] = deduped

        group = QGroupBox(tr("sr.trans_group"))
        trans_lines = []
        gl = QVBoxLayout(group)

        tn_found = {n: ms for n, ms in tn_matches.items() if ms}
        if tn_found:
            trans_lines.append(tr("sr.tn_header"))
            for n in sorted(tn_found):
                t_form = _transpose(target, n)
                trans_lines.append(
                    tr("sr.tn_found", n=n, form=_pc_bracket(t_form), count=len(tn_found[n])))
        else:
            trans_lines.append(tr("sr.tn_none"))

        for label, matches, form in [
            ("P", p_matches, p_form),
            ("I", i_matches, i_form),
            ("R", r_matches, r_form),
            ("RI", ri_matches, ri_form),
        ]:
            if matches:
                trans_lines.append(
                    tr("sr.trans_found", label=label, form=_pc_bracket(form), n=len(matches)))
            else:
                trans_lines.append(
                    tr("sr.trans_none", label=label, form=_pc_bracket(form)))
        
        edit = QTextEdit()
        edit.setReadOnly(True)
        edit.setPlainText("\n".join(trans_lines))
        edit.setHorizontalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        edit.setVerticalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        edit.setMinimumHeight(min(len(trans_lines) * 25 + 10, 300))
        gl.addWidget(edit)
        self._results_layout.addWidget(group)
