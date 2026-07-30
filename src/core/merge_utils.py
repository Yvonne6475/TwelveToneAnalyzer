"""Shared merge utilities for cross-tab custom merge support.
"""
from music21 import chord, note as m21note
from src.core.score_analyzer import diagnose_all_parts
from src.utils.i18n import tr

from PyQt5.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QGroupBox, QLabel, QLineEdit,
    QCheckBox, QSpinBox, QPushButton, QMessageBox,
    QListWidget, QDialogButtonBox,
)
from PyQt5.QtCore import Qt as _Qt


def select_merge_items(parent, all_items, bar_items):
    """Dialog with checkable merge items showing [Bar Merge]/[Chord] labels."""
    _dlg = QDialog(parent)
    _dlg.setWindowTitle(tr("forte.from_chord_title"))
    _dlg.setMinimumSize(500, 400)
    _lay = QVBoxLayout(_dlg)
    _chk_all = QCheckBox(tr("forte.select_all"))
    _chk_all.setChecked(True)
    _lay.addWidget(_chk_all)
    _lst = QListWidget()
    for _i, _it in enumerate(all_items):
        _pc = " ".join(map(str, _it["pcs"]))
        if 'part_name' in _it:
            _seq = " ".join(map(str, _it.get('seq', _it['pcs'])))
            _lab = f"[Part Merge] {_it['part_name']} (Bars {_it['bar_start']}-{_it['bar_end']}): Constituents: [{_seq}] Forte: {_it['forte']}"
        elif 'parts' in _it:
            _seq_pc = " ".join(map(str, _it.get('orig_seq', _it['pcs'])))
            _lab = f"[Bar Merge] Bar {_it['bar']}: [{_seq_pc}] Forte: {_it['forte']}"
            if _it.get('parts'):
                _lab += f" ({_it['parts']})"
        elif 'offset' in _it:
            _pc_str = " ".join(map(str, _it.get('pcs', _it['pcs'])))
            _lab = f"[Offset Merge] Bar {_it['bar']} offset {_it['offset']}: [{_pc_str}] Forte: {_it['forte']}"
            if _it.get('offset_pcs'):
                _lab += f" ({_it['offset_pcs']})"
        else:
            _chord_pc = " ".join(map(str, _it.get('orig_pcs', _it['pcs'])))
            _lab = f"[Chord] Bar {_it['bar']}: [{_chord_pc}] Forte: {_it['forte']}"
            if _it.get('part'):
                _lab += f" ({_it['part']})"
        _lst.addItem(_lab)
        _lst.item(_lst.count()-1).setCheckState(_Qt.Checked)
        _lst.item(_lst.count()-1).setData(_Qt.UserRole, _pc)
    _lay.addWidget(_lst, 1)
    _chk_all.toggled.connect(lambda c: [_lst.item(i).setCheckState(_Qt.Checked if c else _Qt.Unchecked) for i in range(_lst.count())])
    _btn = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
    _btn.accepted.connect(_dlg.accept)
    _btn.rejected.connect(_dlg.reject)
    _lay.addWidget(_btn)
    if _dlg.exec_() != QDialog.Accepted:
        return None
    _sel = []
    for i in range(_lst.count()):
        if _lst.item(i).checkState() == _Qt.Checked:
            _sel.append(_lst.item(i).data(_Qt.UserRole))
    return _sel


def merge_from_score(score, selected_parts: set, start: int, end: int, with_offsets=False):
    """Extract notes. Returns (part_bar_data, all_pcs) or with with_offsets: (data, all_pcs, offset_data)."""
    from collections import OrderedDict
    data = OrderedDict()
    offset_data = {}
    all_pcs = []
    for pi, part in enumerate(score.parts):
        if pi not in selected_parts:
            continue
        pn = part.partName if part.partName else f"Part {pi+1}"
        data[pn] = OrderedDict()
        meas_all = list(part.getElementsByClass('Measure'))
        meas_range = [m for m in meas_all if start <= m.number <= end]
        if not meas_range:
            continue
        for m in meas_range:
            bn = m.number
            for el in m.recurse():
                if isinstance(el, m21note.Note):
                    data[pn].setdefault(bn, []).append(el.pitch.pitchClass)
                    all_pcs.append(el.pitch.pitchClass)
                    if with_offsets:
                        ok = (bn, round(el.offset, 3))
                        offset_data.setdefault(ok, {}).setdefault(pn, []).append(el.pitch.pitchClass)
                elif isinstance(el, chord.Chord):
                    for p in el.pitches:
                        data[pn].setdefault(bn, []).append(p.pitchClass)
                        all_pcs.append(p.pitchClass)
                        if with_offsets:
                            ok = (bn, round(el.offset, 3))
                            offset_data.setdefault(ok, {}).setdefault(pn, []).append(p.pitchClass)
    if with_offsets:
        return data, all_pcs, offset_data
    return data, all_pcs


class MergeSelectorDialog(QDialog):
    """Dialog: select parts & bars, then extract merged PCs."""
    def __init__(self, score, parent=None):
        super().__init__(parent)
        self._score = score
        self._part_checks = {}
        self._result = None
        self.setWindowTitle(tr("tt.merge_title"))
        self.setMinimumSize(450, 300)
        self._setup_ui()

    def _setup_ui(self):
        layout = QVBoxLayout(self)
        part_group = QGroupBox(tr("chord.part_label"))
        part_layout = QHBoxLayout(part_group)
        for d in diagnose_all_parts(self._score) if self._score else []:
            cb = QCheckBox(d.part_name or f"Part {d.index+1}")
            cb.setChecked(True)
            cb.setProperty("part_idx", d.index)
            self._part_checks[f"{d.index}"] = cb
            part_layout.addWidget(cb)
        layout.addWidget(part_group)
        bar_row = QHBoxLayout()
        bar_row.addWidget(QLabel(tr("tt.custom_bars_label")))
        self._bars_input = QLineEdit()
        self._bars_input.setPlaceholderText("1, 3, 5-10, 12, 15-20")
        self._bars_input.setText("")
        bar_row.addWidget(self._bars_input)
        layout.addLayout(bar_row)
        self._btn_merge = QPushButton(tr("tt.btn_merge_search"))
        self._btn_merge.clicked.connect(self._do_merge)
        layout.addWidget(self._btn_merge)
        layout.addStretch()
        close_btn = QPushButton(tr("forte.btn_close"))
        close_btn.clicked.connect(self.close)
        layout.addWidget(close_btn)

    def _parse_bars(self, text: str) -> set:
        bars = set()
        for part in text.split(","):
            part = part.strip()
            if not part: continue
            if "-" in part:
                try:
                    a, b = part.split("-", 1)
                    bars.update(range(int(a.strip()), int(b.strip()) + 1))
                except ValueError: pass
            else:
                try: bars.add(int(part))
                except ValueError: pass
        return bars

    def _do_merge(self):
        if not self._score:
            QMessageBox.warning(self, "", tr("tt.merge_no_score"))
            return
        selected = set()
        for cb in self._part_checks.values():
            if cb.isChecked():
                pi = cb.property("part_idx")
                if pi is not None:
                    selected.add(int(pi))
        if not selected:
            QMessageBox.warning(self, "", tr("tt.merge_no_part"))
            return
        bars = self._parse_bars(self._bars_input.text().strip())
        if not bars:
            QMessageBox.warning(self, "", "Invalid bar list")
            return
        s, e = min(bars), max(bars)
        data, all_pcs, offset_data = merge_from_score(self._score, selected, s, e, with_offsets=True)
        if not all_pcs:
            QMessageBox.warning(self, "", tr("tt.merge_no_notes"))
            return
        # Filter to only selected bars
        for pn in list(data.keys()):
            for bn in list(data[pn].keys()):
                if bn not in bars:
                    del data[pn][bn]
            if not data[pn]:
                del data[pn]
        self._result = (data, all_pcs, offset_data)
        self.accept()

    def get_result(self):
        return self._result  # (data, all_pcs, offset_data = {})
