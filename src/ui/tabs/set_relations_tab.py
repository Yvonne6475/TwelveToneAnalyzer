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


def _compute_forms(normal):
    """Compute P, I, R, RI from normal-order pitch-class list."""
    if not normal:
        return [], [], [], []
    first = normal[0]
    p_form = list(normal)
    i_form = [(2 * first - p) % 12 for p in p_form]
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

        results = chord_tab._results

        # 1) Merge by bar
        bar_sets = {}
        for r in results:
            bar_sets.setdefault(r.bar, set()).update(r.pc_set)
        bar_lines = []
        for bar in sorted(bar_sets):
            pc = sorted(bar_sets[bar])
            if pc:
                bar_lines.append(_pc_str(pc))

        # 2) Individual unique pc_sets
        seen = set()
        indiv_lines = []
        for r in results:
            key = tuple(sorted(r.pc_set))
            if key not in seen:
                seen.add(key)
                indiv_lines.append(_pc_str(r.pc_set))
        indiv_lines.sort(key=lambda x: len(x.split()), reverse=True)

        all_lines = bar_lines + indiv_lines

        self._universe_edit.setText("\n".join(all_lines))

        # Populate combo: bar-merged first (with "Bar" prefix), then individual (with Forte name)
        self._target_combo.blockSignals(True)
        self._target_combo.clear()
        for bar in sorted(bar_sets):
            pc = sorted(bar_sets[bar])
            if pc:
                label = tr("sr.combo_bar", bar=bar, pc=_pc_str(pc), forte=_forte(pc))
                self._target_combo.addItem(label, _pc_str(pc))
        for r in results:
            label = tr("sr.combo_item", pc=_pc_str(r.pc_set), forte=_forte(r.pc_set))
            dup = False
            for i in range(self._target_combo.count()):
                if self._target_combo.itemData(i) == _pc_str(r.pc_set):
                    dup = True
                    break
            if not dup:
                self._target_combo.addItem(label, _pc_str(r.pc_set))
        self._target_combo.blockSignals(False)

        if all_lines:
            self._target_combo.setCurrentIndex(0)

        self._adjust_combo_dropdown_width()

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
            gl.addWidget(QLabel(tr("sr.none")))
        else:
            for item in items:
                gl.addWidget(QLabel(item))
        self._results_layout.addWidget(group)

    def _display_complex(self, cpx, nexus_info=None):
        self._clear_results()

        target = cpx["target"]
        comp = cpx["complement"]
        iv = cpx["interval_vector"]

        # Precompute all Forte names and IVs to avoid redundant chord.Chord() calls
        all_sets = [target, comp] + cpx["subsets"] + cpx["supersets"] + \
                   cpx["z_related"] + cpx["k_related"] + cpx["invariants"]
        forte_cache = {}
        iv_cache_all = {}
        for s in all_sets:
            t = tuple(sorted(s))
            if t not in forte_cache:
                forte_cache[t] = _forte(s)
                iv_cache_all[t] = str(interval_vector(s))

        def _fmt(s):
            t = tuple(sorted(s))
            return tr("sr.rel_item", pc=_pc_str(s),
                      forte=forte_cache[t], iv=iv_cache_all[t])

        # Basic info
        info_group = QGroupBox(tr("sr.info_group"))
        info_layout = QVBoxLayout(info_group)
        info_layout.addWidget(QLabel(
            tr("sr.info_target", pc=_pc_str(target),
               forte=forte_cache[tuple(sorted(target))], iv=str(iv))))
        info_layout.addWidget(QLabel(
            tr("sr.info_complement", pc=_pc_str(comp),
               forte=forte_cache[tuple(sorted(comp))])))

        # intervals of target (consecutive in normal order)
        normal = list(chord.Chord(target).normalOrder)
        intervals = [normal[i+1] - normal[i] for i in range(len(normal) - 1)] if len(normal) >= 2 else []
        info_layout.addWidget(QLabel(
            tr("sr.info_intervals", pc=_pc_str(normal),
               intervals=" ".join(map(str, intervals)))))

        if nexus_info:
            candidates = nexus_info.get("nexus_candidates", [nexus_info.get("nexus")])
            nexus_label = ", ".join(_pc_str(c) for c in candidates)
            info_layout.addWidget(QLabel(
                tr("sr.info_nexus", pc=nexus_label, score=nexus_info["score"])))
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
        """Search the universe for sets matching P, I, R, RI forms of the target."""
        target = cpx["target"]
        normal = list(chord.Chord(target).normalOrder)
        p_form, i_form, r_form, ri_form = _compute_forms(normal)

        # search universe for exact ordered matches
        p_matches, i_matches, r_matches, ri_matches = [], [], [], []
        for s in self._universe:
            if s == p_form:
                p_matches.append(s)
            if s == i_form:
                i_matches.append(s)
            if s == r_form:
                r_matches.append(s)
            if s == ri_form:
                ri_matches.append(s)

        group = QGroupBox(tr("sr.trans_group"))
        gl = QVBoxLayout(group)

        for label, matches, form in [
            ("P", p_matches, p_form),
            ("I", i_matches, i_form),
            ("R", r_matches, r_form),
            ("RI", ri_matches, ri_form),
        ]:
            if matches:
                gl.addWidget(QLabel(
                    tr("sr.trans_found", label=label, form=_pc_bracket(form),
                       n=len(matches))))
            else:
                gl.addWidget(QLabel(
                    tr("sr.trans_none", label=label, form=_pc_bracket(form))))

        self._results_layout.addWidget(group)
