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
        self._target_combo.setSizeAdjustPolicy(QComboBox.AdjustToContents)
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
        layout.addLayout(target_row)

        # ── Results (scrollable) ──
        self._results_widget = QWidget()
        self._results_layout = QVBoxLayout(self._results_widget)
        self._results_layout.setContentsMargins(0, 0, 0, 0)
        self._results_layout.setSpacing(6)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
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
        lines = [l.strip() for l in text.splitlines() if l.strip()]
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
        fm = self._target_combo.fontMetrics()
        max_w = 0
        for i in range(self._target_combo.count()):
            max_w = max(max_w, fm.boundingRect(self._target_combo.itemText(i)).width())
        view = self._target_combo.view()
        if view:
            view.setMinimumWidth(min(max_w + 40, 800))

    def _sync_combo_from_universe(self):
        if self._target_combo.count() > 0:
            return
        self._target_combo.blockSignals(True)
        for s in self._universe:
            pc_str = _pc_str(s)
            if self._target_combo.findData(pc_str) < 0:
                self._target_combo.addItem(
                    tr("sr.combo_item", pc=pc_str, forte=_forte(s)), pc_str)
        self._target_combo.blockSignals(False)
        self._adjust_combo_dropdown_width()

    def _clear_results(self):
        while self._results_layout.count():
            item = self._results_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

    def _add_section(self, title: str, items: list[str]):
        group = QGroupBox(title)
        gl = QVBoxLayout(group)
        if not items:
            lbl = QLabel(tr("sr.none"))
            lbl.setTextInteractionFlags(Qt.TextSelectableByMouse)
            gl.addWidget(lbl)
        else:
            for item in items:
                lbl = QLabel(item)
                lbl.setTextInteractionFlags(Qt.TextSelectableByMouse)
                gl.addWidget(lbl)
        self._results_layout.addWidget(group)

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
            merged = ""
            bar_str = ""
            if t in self._merged_sets:
                bar_info = self._bar_info.get(t, "")
                cons = self._merged_constituents.get(t, set())
                if cons:
                    parts = []
                    for pcs, part in sorted(cons, key=lambda x: (tuple(x[0]), x[1])):
                        parts.append(f"[{' '.join(map(str, pcs))}]({part})")
                    merged = f" [merged {bar_info}: " + " + ".join(parts) + "]"
                else:
                    merged = f" [merged] ({bar_info})" if bar_info else " [merged]"
            else:
                bar_str = self._bar_info.get(t, "")
                if bar_str:
                    bar_str = f" ({bar_str})"
            return tr("sr.rel_item", pc=_pc_str(s),
                      forte=forte_cache[t], iv=iv_cache_all[t],
                      prime=prime_cache[t], intervals=intervals_cache[t],
                      normal=normal_cache[t]) + merged + bar_str

        # Basic info
        info_group = QGroupBox(tr("sr.info_group"))
        info_layout = QVBoxLayout(info_group)
        lbl_target = QLabel(
            tr("sr.info_target", pc=_pc_str(target),
               forte=forte_cache[tuple(sorted(target))], iv=str(iv)))
        lbl_target.setTextInteractionFlags(Qt.TextSelectableByMouse)
        info_layout.addWidget(lbl_target)
        lbl_comp = QLabel(
            tr("sr.info_complement", pc=_pc_str(comp),
               forte=forte_cache[tuple(sorted(comp))]))
        lbl_comp.setTextInteractionFlags(Qt.TextSelectableByMouse)
        info_layout.addWidget(lbl_comp)

        # intervals of target (consecutive in normal order)
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

    def _add_transformation_section(self, cpx):
        """Search the universe for T_n, P, I, R, RI matches of the target."""
        target = cpx["target"]
        normal = list(chord.Chord(target).normalOrder)
        p_form, i_form, r_form, ri_form = _compute_forms(normal)

        # search universe for exact ordered matches
        p_matches, i_matches, r_matches, ri_matches = [], [], [], []
        tn_matches = {}  # n → [matching sets]
        for s in self._universe:
            if s == p_form:
                p_matches.append(s)
            if s == i_form:
                i_matches.append(s)
            if s == r_form:
                r_matches.append(s)
            if s == ri_form:
                ri_matches.append(s)
            # Check all T_n transpositions
            for n in range(12):
                if s == _transpose(target, n):
                    tn_matches.setdefault(n, []).append(s)

        group = QGroupBox(tr("sr.trans_group"))
        gl = QVBoxLayout(group)

        def _bar_parts_str(s):
            """Aggregate bar/part info for a matched set s from _bar_info."""
            key = tuple(sorted(s))
            m = ""
            if key in self._merged_sets:
                bar_info = self._bar_info.get(key, "")
                cons = self._merged_constituents.get(key, set())
                if cons:
                    parts = []
                    for pcs, part in sorted(cons, key=lambda x: (tuple(x[0]), x[1])):
                        parts.append(f"[{' '.join(map(str, pcs))}]({part})")
                    m = f" [merged {bar_info}: " + " + ".join(parts) + "]"
                else:
                    m = f" [merged] ({bar_info})" if bar_info else " [merged]"
            return m

        # T_n section (only show non-empty levels)
        tn_found = {n: ms for n, ms in tn_matches.items() if ms}
        if tn_found:
            lbl_hdr = QLabel(tr("sr.tn_header"))
            lbl_hdr.setTextInteractionFlags(Qt.TextSelectableByMouse)
            gl.addWidget(lbl_hdr)
            for n in sorted(tn_found):
                t_form = _transpose(target, n)
                # Collect unique bar/part info across all matches at this T_n level
                bar_parts = set()
                for ms in tn_found[n]:
                    bp = _bar_parts_str(ms)
                    if bp:
                        bar_parts.add(bp)
                bp_str = "  (" + "; ".join(sorted(bar_parts)) + ")" if bar_parts else ""
                lbl_tn = QLabel(
                    tr("sr.tn_found", n=n, form=_pc_bracket(t_form), count=len(tn_found[n])) + bp_str)
                lbl_tn.setTextInteractionFlags(Qt.TextSelectableByMouse)
                gl.addWidget(lbl_tn)
        else:
            gl.addWidget(QLabel(tr("sr.tn_none")))

        # P / I / R / RI
        for label, matches, form in [
            ("P", p_matches, p_form),
            ("I", i_matches, i_form),
            ("R", r_matches, r_form),
            ("RI", ri_matches, ri_form),
        ]:
            if matches:
                # Collect unique bar/part info across all matches
                bar_parts = set()
                for ms in matches:
                    bp = _bar_parts_str(ms)
                    if bp:
                        bar_parts.add(bp)
                bp_str = "  (" + "; ".join(sorted(bar_parts)) + ")" if bar_parts else ""
                lbl_trans = QLabel(
                    tr("sr.trans_found", label=label, form=_pc_bracket(form),
                       n=len(matches)) + bp_str)
                lbl_trans.setTextInteractionFlags(Qt.TextSelectableByMouse)
                gl.addWidget(lbl_trans)
            else:
                gl.addWidget(QLabel(
                    tr("sr.trans_none", label=label, form=_pc_bracket(form))))

        self._results_layout.addWidget(group)
