"""Inclusion Lattice tab: visualize subset relations in pitch-class sets."""

from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QGroupBox, QLabel,
    QLineEdit, QSpinBox, QPushButton, QComboBox, QTextEdit,
    QFileDialog, QMessageBox, QScrollArea,
)
from PyQt5.QtCore import Qt

import matplotlib.pyplot as plt
import networkx as nx
from music21 import chord

from src.core.inclusion_lattice import (
    generate_all_subsets, build_inclusion_graph,
    compute_layout, build_labels, get_forte_class,
)
from src.ui.widgets.score_opener import setup_open_menu
from src.ui.widgets.plot_canvas import PlotCanvas
from src.utils.i18n import tr


class LatticeTab(QWidget):
    def __init__(self, main_window=None):
        super().__init__()
        self._main_window = main_window
        self._chord_entries = []
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

        # Input controls
        ctrl_group = QGroupBox(tr("lattice.ctrl_group"))
        ctrl_layout = QHBoxLayout(ctrl_group)

        ctrl_layout.addWidget(QLabel(tr("lattice.input_label")))
        self._input_edit = QLineEdit()
        self._input_edit.setPlaceholderText("0 2 4 7 9  (e.g. C D E G A)")
        ctrl_layout.addWidget(self._input_edit, 1)

        ctrl_layout.addWidget(QLabel(tr("lattice.min_size")))
        self._spin_min = QSpinBox()
        self._spin_min.setMinimum(2)
        self._spin_min.setMaximum(5)
        self._spin_min.setValue(3)
        ctrl_layout.addWidget(self._spin_min)

        ctrl_layout.addWidget(QLabel(tr("lattice.max_size")))
        self._spin_max = QSpinBox()
        self._spin_max.setMinimum(3)
        self._spin_max.setMaximum(8)
        self._spin_max.setValue(6)
        ctrl_layout.addWidget(self._spin_max)

        ctrl_layout.addStretch()

        self._btn_generate = QPushButton(tr("lattice.btn_generate"))
        self._btn_generate.setProperty("accent", "teal")
        self._btn_generate.clicked.connect(self._on_generate)
        ctrl_layout.addWidget(self._btn_generate)

        layout.addWidget(ctrl_group)

        # Batch collections analysis
        coll_group = QGroupBox(tr("lattice.collections_group"))
        coll_layout = QVBoxLayout(coll_group)
        self._collections_edit = QTextEdit()
        self._collections_edit.setPlaceholderText(tr("lattice.collections_placeholder"))
        self._collections_edit.setMaximumHeight(60)
        self._collections_edit.setMinimumHeight(40)
        coll_layout.addWidget(self._collections_edit)

        coll_btn_row = QHBoxLayout()
        self._btn_analyze_coll = QPushButton(tr("lattice.btn_analyze_collections"))
        self._btn_analyze_coll.clicked.connect(self._on_analyze_collections)
        coll_btn_row.addWidget(self._btn_analyze_coll)
        coll_btn_row.addStretch()
        coll_layout.addLayout(coll_btn_row)
        layout.addWidget(coll_group)

        # Plot area (scrollable for large lattices)
        self._canvas = PlotCanvas(self)
        self._scroll_area = QScrollArea()
        self._scroll_area.setWidgetResizable(False)
        self._scroll_area.setWidget(self._canvas)
        layout.addWidget(self._scroll_area, 1)

        # Quick-action: extract from twelve-tone row or chord analysis
        quick_row = QHBoxLayout()
        self._btn_from_row = QPushButton(tr("lattice.btn_from_row"))
        self._btn_from_row.setEnabled(False)
        self._btn_from_row.clicked.connect(self._on_from_row)
        quick_row.addWidget(self._btn_from_row)

        self._btn_from_chord = QPushButton(tr("lattice.btn_from_chord"))
        self._btn_from_chord.setEnabled(False)
        self._btn_from_chord.clicked.connect(self._on_from_chord)
        quick_row.addWidget(self._btn_from_chord)

        self._chord_combo = QComboBox()
        self._chord_combo.setMinimumWidth(320)
        self._chord_combo.setSizeAdjustPolicy(QComboBox.AdjustToContents)
        self._chord_combo.setEnabled(False)
        self._chord_combo.currentIndexChanged.connect(self._on_chord_combo_changed)
        quick_row.addWidget(self._chord_combo, 1)

        self._btn_save = QPushButton(tr("lattice.btn_save"))
        self._btn_save.setEnabled(False)
        self._btn_save.clicked.connect(self._on_save)
        quick_row.addWidget(self._btn_save)
        quick_row.addStretch()
        layout.addLayout(quick_row)

    def on_score_loaded(self, score=None, path=None):
        mw = self._main_window
        if mw and mw.score:
            self._score = mw.score
            self._btn_from_row.setEnabled(True)
            self._btn_from_chord.setEnabled(True)

    def _on_generate(self):
        text = self._input_edit.text().strip()
        if not text:
            QMessageBox.warning(self, tr("lattice.input_error"), tr("lattice.no_input"))
            return
        try:
            pc_set = list(map(int, text.split()))
        except ValueError:
            QMessageBox.warning(self, tr("lattice.input_error"), tr("lattice.invalid_input"))
            return

        min_sz = self._spin_min.value()
        max_sz = self._spin_max.value()
        if max_sz < min_sz:
            QMessageBox.warning(self, tr("lattice.input_error"), tr("lattice.size_error"))
            return

        self._draw_lattice(pc_set, min_sz, max_sz)

    def _draw_lattice(self, pc_set: list[int], min_size: int, max_size: int):
        subsets = generate_all_subsets(pc_set, min_size, max_size)
        if not subsets:
            QMessageBox.warning(self, tr("lattice.input_error"),
                                tr("lattice.no_subsets", count=len(pc_set)))
            return

        G, levels = build_inclusion_graph(subsets)
        pos = compute_layout(levels)
        labels = build_labels(G)

        self._current_fig_data = (G, pos, labels, pc_set, min_size, max_size)

        # Dynamic figure size based on graph complexity
        num_levels = len(levels)
        max_nodes = max((len(v) for v in levels.values()), default=1)
        node_count = len(G.nodes())
        w = max(6, min(28, 4 + max_nodes * 2.2))
        h = max(4, min(24, 2 + num_levels * 1.6))

        self._canvas.clear()
        self._canvas.set_size_inches(w, h)
        ax = self._canvas.fig.add_subplot(111)

        # Adjust node/font size based on complexity
        n_size = max(1500, min(6000, 8000 - node_count * 120))
        f_size = max(6, min(14, 16 - node_count * 0.3))

        nx.draw(G, pos, ax=ax,
                labels=labels,
                node_color="white",
                edgecolors="black",
                linewidths=2,
                node_size=n_size,
                font_size=f_size,
                font_weight="bold")

        title = f"Inclusion Lattice ({min_size}-{max_size} tones) | "
        title += ", ".join(map(str, sorted(set(pc_set))))
        ax.set_title(title, fontsize=14)
        ax.axis("off")
        self._canvas.fig.tight_layout()
        self._canvas.draw()
        self._btn_save.setEnabled(True)

    def _on_from_row(self):
        """Try to get a 12-tone row from the twelve-tone tab."""
        mw = self._main_window
        if not mw:
            return
        tt = mw._twelve_tone_tab
        if hasattr(tt, '_row') and tt._row:
            self._input_edit.setText(" ".join(map(str, tt._row)))
        else:
            QMessageBox.information(self, tr("lattice.from_row_title"),
                                    tr("lattice.no_row_msg"))

    def _on_from_chord(self):
        """Import pc_sets from the chord analysis tab and populate the combo."""
        mw = self._main_window
        if not mw:
            return
        chord_tab = mw._chord_tab
        if not hasattr(chord_tab, '_results') or not chord_tab._results:
            QMessageBox.information(self, tr("lattice.from_row_title"),
                                    tr("lattice.no_chord_msg"))
            return

        results = chord_tab._results

        # 1) Merge by bar: union of all parts' pc_sets within the same measure
        bar_sets = {}
        for r in results:
            bar_sets.setdefault(r.bar, set()).update(r.pc_set)
        bar_entries = []
        for bar in sorted(bar_sets):
            pc = sorted(bar_sets[bar])
            if pc:
                bar_entries.append((pc, f"Bar {bar}"))

        # 2) Individual chord entries
        seen = set()
        chord_entries = []
        for r in results:
            key = tuple(r.pc_set)
            if key not in seen:
                seen.add(key)
                chord_entries.append((list(r.pc_set), r.forte_class))

        self._chord_entries = []
        self._chord_combo.blockSignals(True)
        self._chord_combo.clear()

        for pc, fc in bar_entries:
            self._chord_entries.append(pc)
            label = f"[Bar merge] {' '.join(map(str, pc))}  (size={len(pc)}, {fc})"
            self._chord_combo.addItem(label)

        for pc, fc in sorted(chord_entries, key=lambda x: len(x[0]), reverse=True):
            self._chord_entries.append(pc)
            label = f"{' '.join(map(str, pc))}  (size={len(pc)}, {fc})"
            self._chord_combo.addItem(label)

        self._chord_combo.blockSignals(False)
        # Expand popup width to show full item text
        fm = self._chord_combo.fontMetrics()
        max_label_width = max((fm.horizontalAdvance(self._chord_combo.itemText(i))
                               for i in range(self._chord_combo.count())), default=0)
        self._chord_combo.view().setMinimumWidth(max_label_width + 40)
        self._chord_combo.setEnabled(True)
        if self._chord_entries:
            self._chord_combo.setCurrentIndex(0)

    def _on_analyze_collections(self):
        """Parse multi-line pc-sets, classify each, and load into the combo."""
        text = self._collections_edit.toPlainText().strip()
        if not text:
            QMessageBox.warning(self, tr("lattice.input_error"),
                                tr("lattice.collections_empty"))
            return

        lines = [l.strip() for l in text.splitlines() if l.strip()]
        self._chord_entries = []
        self._chord_combo.blockSignals(True)
        self._chord_combo.clear()

        for line in lines:
            try:
                pcs = list(map(int, line.split()))
            except ValueError:
                continue
            if not pcs:
                continue
            c = chord.Chord(pcs)
            pc_list = list(c.normalOrder)
            self._chord_entries.append(pc_list)
            label = (f"{' '.join(map(str, pcs))} -> "
                     f"Normal: {c.normalOrder} | "
                     f"Prime: {c.primeFormString} | "
                     f"Forte: {c.forteClass}")
            self._chord_combo.addItem(label)

        self._chord_combo.blockSignals(False)
        if self._chord_entries:
            fm = self._chord_combo.fontMetrics()
            max_label_width = max((fm.horizontalAdvance(self._chord_combo.itemText(i))
                                   for i in range(self._chord_combo.count())), default=0)
            self._chord_combo.view().setMinimumWidth(max_label_width + 40)
            self._chord_combo.setEnabled(True)
            self._chord_combo.setCurrentIndex(0)

    def _on_chord_combo_changed(self, idx: int):
        if idx < 0 or idx >= len(self._chord_entries):
            return
        pc_set = self._chord_entries[idx]
        self._input_edit.setText(" ".join(map(str, pc_set)))
        self._draw_lattice(pc_set, self._spin_min.value(), self._spin_max.value())

    def _on_save(self):
        path, _ = QFileDialog.getSaveFileName(
            self, tr("lattice.save_png"), "inclusion_lattice.png",
            "PNG (*.png);;All Files (*)"
        )
        if path:
            self._canvas.fig.savefig(path, dpi=150, bbox_inches='tight')
            QMessageBox.information(self, tr("lattice.saved"),
                                    tr("dialog.saved_to", path=path))
