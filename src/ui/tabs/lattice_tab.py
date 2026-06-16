"""Inclusion Lattice tab: visualize subset relations in pitch-class sets."""

from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QGroupBox, QLabel,
    QLineEdit, QSpinBox, QPushButton, QComboBox, QTextEdit,
    QFileDialog, QMessageBox, QScrollArea,
)
from PyQt5.QtCore import Qt

import matplotlib.pyplot as plt
import matplotlib.cm as cm
import networkx as nx
from music21 import chord

from src.core.inclusion_lattice import (
    generate_all_subsets, build_inclusion_graph,
    compute_layout, build_labels, get_forte_class,
)
from src.ui.widgets.score_opener import setup_open_menu
from src.ui.widgets.plot_canvas import PlotCanvas
from src.utils.i18n import tr
from src.utils.config import temp_default_path

# ── Readability constants ───────────────────────────────────────────
_MIN_FONT = 8          # minimum pt for node labels
_MAX_FONT = 14         # maximum pt
_MIN_NODE = 1600       # minimum node area (px²)
_TITLE_FONT = 13       # title font size
_ARROW_SIZE = 14       # edge arrow size (larger = more visible)
_DPI = 100             # matplotlib DPI


class LatticeTab(QWidget):
    def __init__(self, main_window=None):
        super().__init__()
        self._main_window = main_window
        self._chord_entries = []
        self._current_fig_data = None
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
        self._spin_min.setMinimum(1)
        self._spin_min.setMaximum(11)
        self._spin_min.setValue(3)
        self._spin_min.setToolTip(tr("lattice.range_hint"))
        ctrl_layout.addWidget(self._spin_min)

        ctrl_layout.addWidget(QLabel(tr("lattice.max_size")))
        self._spin_max = QSpinBox()
        self._spin_max.setMinimum(1)
        self._spin_max.setMaximum(11)
        self._spin_max.setValue(6)
        self._spin_max.setToolTip(tr("lattice.range_hint"))
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

        # Plot area — uses a QScrollArea so large lattices scroll
        self._canvas = PlotCanvas(self)
        self._scroll_area = QScrollArea()
        self._scroll_area.setWidgetResizable(False)
        self._scroll_area.setWidget(self._canvas)
        self._scroll_area.setStyleSheet(
            "QScrollArea { background-color: #fefdfb; border: none; }"
        )
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

        self._btn_chord_relations = QPushButton(tr("lattice.btn_chord_relations"))
        self._btn_chord_relations.setProperty("accent", "teal")
        self._btn_chord_relations.setEnabled(False)
        self._btn_chord_relations.setToolTip(tr("lattice.btn_chord_relations_hint"))
        self._btn_chord_relations.clicked.connect(self._on_chord_relations)
        quick_row.addWidget(self._btn_chord_relations)

        self._btn_save = QPushButton(tr("lattice.btn_save"))
        self._btn_save.setEnabled(False)
        self._btn_save.clicked.connect(self._on_save)
        quick_row.addWidget(self._btn_save)
        quick_row.addStretch()
        layout.addLayout(quick_row)

        self._lbl_edge_hint = QLabel(tr("lattice.edge_hint"))
        self._lbl_edge_hint.setStyleSheet(
            "color: #856404; background-color: #fff3cd; "
            "border: 1px solid #ffc107; border-radius: 3px; "
            "padding: 4px 8px; font-size: 12px;"
        )
        self._lbl_edge_hint.setVisible(False)
        layout.addWidget(self._lbl_edge_hint)

    def on_score_loaded(self, score=None, path=None):
        mw = self._main_window
        # Clear old data and inputs
        self._input_edit.clear()
        self._collections_edit.clear()
        self._chord_entries = []
        self._chord_combo.clear()
        self._chord_combo.setEnabled(False)
        self._btn_chord_relations.setEnabled(False)
        self._btn_save.setEnabled(False)
        self._canvas.clear()
        self._canvas.draw()
        self._lbl_edge_hint.setVisible(False)
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
        if max_sz - min_sz > 4:
            QMessageBox.warning(self, tr("lattice.input_error"), tr("lattice.range_warn"))
            # proceed anyway — user has been warned

        self._btn_generate.setEnabled(False); self._btn_generate.repaint()
        from PyQt5.QtWidgets import QApplication; QApplication.processEvents()
        QApplication.setOverrideCursor(Qt.WaitCursor)
        self._draw_lattice(pc_set, min_sz, max_sz)
        self._btn_generate.setEnabled(True); QApplication.restoreOverrideCursor()

    # ── Drawing helpers ───────────────────────────────────────────

    def _calc_figure_size(self, G, pos, levels):
        """Compute readable figure dimensions from the graph layout.

        Returns (fig_w_inches, fig_h_inches, node_size_px, font_size_pt).
        """
        node_count = len(G.nodes())
        if node_count == 0:
            return 8, 6, _MIN_NODE, _MAX_FONT

        # Bound the layout in data coordinates
        xs = [p[0] for p in pos.values()]
        ys = [p[1] for p in pos.values()]
        data_w = max(1.0, max(xs) - min(xs))
        data_h = max(1.0, max(ys) - min(ys))
        aspect = data_w / max(data_h, 0.5)

        max_pc_len = max((len(n) for n in G.nodes()), default=3)

        # Font: shrink as label length grows, but keep readable
        font_size = max(_MIN_FONT, _MAX_FONT - max(0, max_pc_len - 3) * 1.1)

        # Estimate how many inches we need so labels don't overlap.
        # A single-line label needs ~0.12 inches per character at `font_size` pt.
        char_w_in = max_pc_len * font_size * 0.01
        # Each node column needs at least that much horizontal room
        max_nodes_per_level = max((len(v) for v in levels.values()), default=1)
        num_levels = len(levels)

        need_w = max_nodes_per_level * (char_w_in + 0.55) + 0.8   # margins
        need_h = num_levels * (font_size * 0.025 + 0.45) + 0.8

        # Match viewport: if the lattice is compact, expand to fill ~85 %
        # of the viewport so it feels spacious instead of tiny.
        vp = self._scroll_area.viewport()
        if vp:
            vp_w = vp.width() / _DPI
            vp_h = vp.height() / _DPI
            need_w = max(need_w, vp_w * 0.80)
            need_h = max(need_h, vp_h * 0.75)

        fig_w = max(8, min(35, need_w))
        fig_h = max(6, min(28, need_h))

        # Node size: base area + bonus for long labels, minus a small
        # penalty for very dense graphs (so nodes don't completely fill).
        node_size = max(_MIN_NODE, 1200 + max_pc_len * 480 - max(0, node_count - 12) * 35)

        return fig_w, fig_h, node_size, font_size

    def _render_graph(self, G, levels, pos, labels, title, is_chord_relations=False):
        """Draw the graph onto the canvas with colored edges and arrows."""
        fig_w, fig_h, n_size, f_size = self._calc_figure_size(G, pos, levels)

        self._canvas.clear()
        self._canvas.set_size_inches(fig_w, fig_h)
        ax = self._canvas.fig.add_subplot(111)

        # ── Color map for edges ──
        sources = [n for n in G.nodes() if G.out_degree(n) > 0]
        if sources:
            sorted_sources = sorted(sources, key=lambda n: (-pos[n][1], pos[n][0]))
            n_palette = 20
            step = 7
            color_indices = [(i * step) % n_palette for i in range(len(sorted_sources))]
            source_colors = cm.tab20(color_indices)
            color_map = dict(zip(sorted_sources, source_colors))
        else:
            color_map = {}

        # Edge style — use the SAME node_size as draw_networkx_nodes so
        # edges start/end exactly at the circle boundary.  Nodes are
        # drawn AFTER edges (white fill, black border) layering cleanly
        # on top of the arrowhead while the shaft remains visible.
        edge_kw = dict(
            ax=ax, arrows=True, arrowsize=_ARROW_SIZE,
            node_size=n_size,
            node_shape='o',
            connectionstyle='arc3,rad=0.0',
        )

        for src in sources:
            edges = list(G.out_edges(src))
            if edges:
                nx.draw_networkx_edges(
                    G, pos, edgelist=edges,
                    edge_color=[color_map[src]] * len(edges),
                    width=2.0, **edge_kw,
                )

        drawn_edges = set()
        for src in sources:
            for e in G.out_edges(src):
                drawn_edges.add(e)
        remaining = [e for e in G.edges() if e not in drawn_edges]
        if remaining:
            nx.draw_networkx_edges(
                G, pos, edgelist=remaining,
                edge_color="gray", width=1.5, **edge_kw,
            )

        nx.draw_networkx_nodes(G, pos, ax=ax,
                               node_color="white", edgecolors="black",
                               linewidths=2, node_size=n_size)
        nx.draw_networkx_labels(G, pos, ax=ax,
                                labels=labels, font_size=f_size,
                                font_weight="bold")

        ax.set_title(title, fontsize=_TITLE_FONT, pad=10)
        ax.axis("off")
        self._canvas.fig.tight_layout(pad=1.0)
        self._canvas.draw()
        self._btn_save.setEnabled(True)
        self._lbl_edge_hint.setVisible(is_chord_relations)

    # ── Public API ────────────────────────────────────────────────

    def _draw_lattice(self, pc_set: list[int], min_size: int, max_size: int):
        subsets = generate_all_subsets(pc_set, min_size, max_size)
        if not subsets:
            QMessageBox.warning(self, tr("lattice.input_error"),
                                tr("lattice.no_subsets", count=len(pc_set)))
            return

        G, levels = build_inclusion_graph(subsets)

        max_pc_len = max((len(n) for n in G.nodes()), default=3)
        x_gap = 1.0 + max_pc_len * 0.45
        y_gap = 0.6 + max_pc_len * 0.25
        pos = compute_layout(levels, x_gap=x_gap, y_gap=y_gap)
        labels = build_labels(G)

        self._current_fig_data = (G, pos, labels, pc_set, min_size, max_size)

        title = f"Inclusion Lattice ({min_size}-{max_size} tones) | "
        title += ", ".join(map(str, sorted(set(pc_set))))
        self._render_graph(G, levels, pos, labels, title)

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
        self._btn_chord_relations.setEnabled(True)
        # Auto-fill first entry — setCurrentIndex may be a no-op if Qt already
        # tracked index 0 during the blocked addItem phase, so fill explicitly.
        if self._chord_entries:
            self._chord_combo.setCurrentIndex(-1)
            self._chord_combo.setCurrentIndex(0)
            self._on_chord_combo_changed(0)

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
            self._btn_chord_relations.setEnabled(True)
            # Auto-fill first entry — setCurrentIndex may be a no-op if Qt already
            # tracked index 0 during the blocked addItem phase, so fill explicitly.
            self._chord_combo.setCurrentIndex(-1)
            self._chord_combo.setCurrentIndex(0)
            self._on_chord_combo_changed(0)

    def _on_chord_combo_changed(self, idx: int):
        if idx < 0 or idx >= len(self._chord_entries):
            return
        pc_set = self._chord_entries[idx]
        self._input_edit.setText(" ".join(map(str, pc_set)))

    def _on_chord_relations(self):
        """Build an inclusion lattice from the chord analysis sets themselves."""
        if not self._chord_entries:
            QMessageBox.information(self, tr("lattice.from_row_title"),
                                    tr("lattice.no_chord_msg"))
            return

        min_sz = self._spin_min.value()
        max_sz = self._spin_max.value()

        filtered = [tuple(sorted(s)) for s in self._chord_entries
                    if min_sz <= len(s) <= max_sz]
        dropped = len(self._chord_entries) - len(filtered)
        if len(filtered) < 2:
            QMessageBox.warning(self, tr("lattice.input_error"),
                                tr("lattice.not_enough_sets_with_dropped",
                                   kept=len(filtered), dropped=dropped,
                                   min_sz=min_sz, max_sz=max_sz))
            return

        G, levels = build_inclusion_graph(filtered)

        max_pc_len = max((len(n) for n in G.nodes()), default=3)
        x_gap = 1.0 + max_pc_len * 0.45
        y_gap = 0.6 + max_pc_len * 0.25
        pos = compute_layout(levels, x_gap=x_gap, y_gap=y_gap)
        labels = build_labels(G)

        title = (f"Chord Relations Lattice ({min_sz}-{max_sz} tones) | "
                 f"{len(G.nodes())} sets, {len(G.edges())} relations")
        self._render_graph(G, levels, pos, labels, title, is_chord_relations=True)

    def _on_save(self):
        if self._canvas is None or self._canvas.fig is None:
            QMessageBox.warning(self, tr("lattice.saved"), tr("lattice.no_fig"))
            return

        path, _ = QFileDialog.getSaveFileName(
            self, tr("lattice.save_png"), temp_default_path("inclusion_lattice.png"),
            "PNG (*.png);;All Files (*)"
        )
        if not path:
            return

        try:
            self._canvas.fig.savefig(path, dpi=150, bbox_inches='tight')
        except (OSError, PermissionError) as e:
            QMessageBox.critical(
                self, tr("lattice.saved"),
                tr("lattice.save_permission_error", error=str(e))
            )
            return

        QMessageBox.information(self, tr("lattice.saved"),
                                tr("dialog.saved_to", path=path))
