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
from src.core.merge_utils import MergeSelectorDialog, select_merge_items
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
        self._lattice_bar_info = {}  # tuple(sorted(pcs)) -> bar_str
        self._lattice_node_info = {}  # tuple(sorted(pcs)) -> source label
        self._lattice_node_full_info = {}  # tuple(sorted(pcs)) -> [(pcs_label, forte, source)]
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
        self._spin_max.setMaximum(12)
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
        self._btn_merge = QPushButton(tr("forte.btn_merge"))
        self._btn_merge.clicked.connect(self._on_merge_from_score)
        quick_row.addWidget(self._btn_merge)

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

        self._btn_temporal_network = QPushButton(tr("lattice.btn_temporal_network"))
        self._btn_temporal_network.setEnabled(False)
        self._btn_temporal_network.setToolTip(tr("lattice.btn_temporal_network_hint"))
        self._btn_temporal_network.clicked.connect(self._on_temporal_network)
        quick_row.addWidget(self._btn_temporal_network)

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
        self._lattice_bar_info = {}  # tuple(sorted(pcs)) -> bar_str
        self._lattice_node_info = {}  # tuple(sorted(pcs)) -> source label
        self._lattice_node_full_info = {}  # tuple(sorted(pcs)) -> [(pcs_label, forte, source)]
        self._chord_combo.clear()
        self._chord_combo.setEnabled(False)
        self._btn_chord_relations.setEnabled(False)
        self._btn_temporal_network.setEnabled(False)
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
        pc_set = []
        for p in text.split():
            try:
                v = int(p)
                if 0 <= v <= 11:
                    pc_set.append(v)
                else:
                    break
            except ValueError:
                break
        if len(pc_set) < 2:
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

    def _calc_figure_size(self, G, pos, levels, labels=None):
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
        max_lines = 1
        max_line_len = max_pc_len
        if labels:
            for lb in labels.values():
                lines = str(lb).splitlines()
                max_lines = max(max_lines, len(lines))
                max_line_len = max(max_line_len, max((len(l) for l in lines), default=1))

        # Font: shrink as label length grows, but keep readable
        font_size = max(_MIN_FONT, _MAX_FONT - max(0, max_line_len - 3) * 0.7)

        # Estimate how many inches we need so labels don't overlap.
        # A single-line label needs ~0.12 inches per character at `font_size` pt.
        char_w_in = max_line_len * font_size * 0.01
        # Each node column needs at least that much horizontal room
        max_nodes_per_level = max((len(v) for v in levels.values()), default=1)
        num_levels = len(levels)

        need_w = max_nodes_per_level * (char_w_in + 0.55) + 0.8   # margins
        need_h = num_levels * (font_size * 0.025 * max_lines + 0.45 * max_lines) + 0.8

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
        node_size = max(_MIN_NODE, 1200 + max_pc_len * 480 + max_lines * 550 - max(0, node_count - 12) * 35)

        return fig_w, fig_h, node_size, font_size

    def _render_graph(self, G, levels, pos, labels, title, is_chord_relations=False):
        """Draw the graph onto the canvas with colored edges and arrows."""
        fig_w, fig_h, n_size, f_size = self._calc_figure_size(G, pos, levels, labels=labels)

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
        self._lattice_node_info = {}
        self._lattice_node_full_info = {}

        # 1) Merge by bar: union of all parts' pc_sets within the same measure
        bar_sets = {}
        for r in results:
            if len(r.pc_set) <= 1:
                continue
            bar_sets.setdefault(r.bar, set()).update(r.pc_set)
        bar_entries = []
        for bar in sorted(bar_sets):
            pc = sorted(bar_sets[bar])
            if pc:
                bar_entries.append((pc, f"Bar {bar}"))

        # 2) Individual entries: dedup for combo, accumulate bar info
        seen = set()
        chord_entries = []
        for r in results:
            if len(r.pc_set) <= 1:
                continue
            key = tuple(r.pc_set)  # already Chords PCs order
            if key not in seen:
                seen.add(key)
                chord_entries.append((list(r.pc_set), r.forte_class))
            if key not in self._lattice_bar_info:
                self._lattice_bar_info[key] = f"Bar {r.bar} ({r.part_name})"
            else:
                existing = self._lattice_bar_info[key]
                entry = f"Bar {r.bar} ({r.part_name})"
                if entry not in existing:
                    self._lattice_bar_info[key] = existing + f"; {entry}"

        self._chord_entries = []
        self._chord_combo.blockSignals(True)
        self._chord_combo.clear()

        # Use _chord_display_rows for consistent per-bar order: part→chord→bar→offset
        ct = self._main_window._chord_tab
        cd = getattr(ct, "_chord_display_rows", [])
        if cd:
            for rw in cd:
                tt = rw["type"]
                ps = rw["pcs"]
                key = tuple(sorted(ps))
                if tt == "offset_merged":
                    off = str(rw.get("offset", "")).replace("offset ", "")
                    src = f"Offset {off}"
                else:
                    src = f"Bar {rw['bar']}"
                self._lattice_node_info.setdefault(key, [])
                if src not in self._lattice_node_info[key]:
                    self._lattice_node_info[key].append(src)
                fc2 = rw.get("forte", chord.Chord(ps).forteClass)
                pcs_label = " ".join(map(str, ps))
                if tt == "indiv":
                    full_src = self._lattice_bar_info.get(
                        tuple(ps), f"Bar {rw['bar']} ({rw.get('part', '')})"
                    )
                elif tt == "part_merged":
                    full_src = f"Bar {rw['bar']} ({rw.get('part', '')} merged)"
                elif tt == "bar_merged":
                    full_src = f"Bar {rw['bar']} (Bar merged)"
                else:
                    off = str(rw.get("offset", "")).replace("offset ", "")
                    full_src = f"Bar {rw['bar']} Offset {off} (Offset merged)"
                self._lattice_node_full_info.setdefault(key, [])
                if (pcs_label, fc2, full_src) not in self._lattice_node_full_info[key]:
                    self._lattice_node_full_info[key].append((pcs_label, fc2, full_src))
                if tt == "indiv":
                    # Skip single notes in lattice
                    if len(ps) <= 1:
                        continue
                    bar_str = self._lattice_bar_info.get(tuple(ps), f"Bar {rw['bar']} ({rw.get('part','')})")
                    self._chord_entries.append(ps)
                    label = f"{' '.join(map(str, ps))}  (size={len(ps)}, {fc2}, {bar_str})"
                    self._chord_combo.addItem(label)
                elif tt in ("part_merged", "bar_merged", "offset_merged"):
                    fc2 = rw.get("forte", chord.Chord(ps).forteClass)
                    self._chord_entries.append(ps)
                    pn = rw.get("part", "")
                    if tt == "part_merged":
                        lb = "[" + pn + " merged] "
                    elif tt == "bar_merged":
                        lb = "[Bar merged] "
                    else:
                        lb = "[Offset merged] "
                    lb += " ".join(map(str, ps)) + "  Forte: " + fc2 + "  (Bar " + str(rw["bar"]) + ")"
                    self._chord_combo.addItem(lb)
        self._chord_combo.blockSignals(False)
        # Expand popup width to show full item text
        fm = self._chord_combo.fontMetrics()
        max_label_width = max((fm.horizontalAdvance(self._chord_combo.itemText(i))
                               for i in range(self._chord_combo.count())), default=0)
        self._chord_combo.view().setMinimumWidth(max_label_width + 40)
        self._chord_combo.setEnabled(True)
        self._btn_chord_relations.setEnabled(True)
        self._btn_temporal_network.setEnabled(True)
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

        lines = [l.strip() for l in text.splitlines() if l.strip() and not l.strip().startswith('#')]
        self._chord_entries = []
        self._lattice_node_full_info = {}
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
            key = tuple(sorted(pc_list))
            self._lattice_node_full_info.setdefault(key, [])
            info = (" ".join(map(str, pcs)), c.forteClass, "Manual")
            if info not in self._lattice_node_full_info[key]:
                self._lattice_node_full_info[key].append(info)
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
            self._btn_temporal_network.setEnabled(True)
            # Auto-fill first entry — setCurrentIndex may be a no-op if Qt already
            # tracked index 0 during the blocked addItem phase, so fill explicitly.
            self._chord_combo.setCurrentIndex(-1)
            self._chord_combo.setCurrentIndex(0)
            self._on_chord_combo_changed(0)

    def _on_chord_combo_changed(self, idx: int):
        if idx < 0 or idx >= len(self._chord_entries):
            return
        full_text = self._chord_combo.itemText(idx)
        self._input_edit.setText(full_text)

    def _on_chord_relations(self):
        """Build an inclusion lattice from the chord analysis sets themselves."""
        if not self._chord_entries:
            QMessageBox.information(self, tr("lattice.from_row_title"),
                                    tr("lattice.no_chord_msg"))
            return

        min_sz = self._spin_min.value()
        max_sz = self._spin_max.value()

        selected_idx = self._chord_combo.currentIndex()
        focus = None
        if 0 <= selected_idx < len(self._chord_entries):
            focus = tuple(sorted(self._chord_entries[selected_idx]))

        filtered = [tuple(sorted(s)) for s in self._chord_entries
                    if min_sz <= len(s) <= max_sz]
        dropped = len(self._chord_entries) - len(filtered)
        if focus is not None:
            focus_set = set(focus)
            filtered = [
                s for s in filtered
                if set(s).issubset(focus_set) or focus_set.issubset(set(s))
            ]
            # Ensure the focus itself is always included even if size-range filtered out
            if focus not in filtered:
                filtered.append(focus)
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
        for node in G.nodes():
            src = self._lattice_node_info.get(tuple(sorted(node)))
            if src:
                labels[node] = f"{labels[node]}\n{'; '.join(src) if isinstance(src, list) else src}"

        title = (f"Chord Relations Lattice ({min_sz}-{max_sz} tones) | "
                 f"{len(G.nodes())} sets, {len(G.edges())} relations")
        self._render_graph(G, levels, pos, labels, title, is_chord_relations=True)

    @staticmethod
    def _compact_source(src: str) -> str:
        """Shorten a source label to Bar/Offset only when it is too long."""
        import re
        if len(src) <= 20:
            return src
        m = re.match(r"(Bars? [0-9]+(?:-[0-9]+)?(?: Offset [0-9.]+)?)", src)
        if m:
            return m.group(1)
        return src[:24]

    def _temporal_node_text(self, node, info_map=None):
        """One line of full info (PCs, Forte, source) for a tree node."""
        info_map = info_map if info_map is not None else self._lattice_node_full_info
        info_list = info_map.get(node)
        if info_list:
            pcs_label, forte, _ = info_list[0]
            srcs = []
            for _pcs, _forte, src in info_list:
                compact = self._compact_source(src)
                if compact not in srcs:
                    srcs.append(compact)
            src_line = " | ".join(srcs[:2])
            return f"{pcs_label} | {forte} | {src_line}"
        return f"{' '.join(map(str, node))} | {get_forte_class(list(node))}"

    def _build_temporal_tree_text(self, G, info_map=None):
        """Render the inclusion network as a plain-text horizontal tree."""
        roots = sorted(
            [n for n in G.nodes() if G.in_degree(n) == 0],
            key=lambda n: (-len(n), n),
        )
        children_of = {}
        placed = set(roots)

        def assign(node):
            children = [
                s for s in sorted(G.successors(node), key=lambda n: (len(n), n))
                if s not in placed
            ]
            children_of[node] = children
            for child in children:
                placed.add(child)
                assign(child)

        for root in roots:
            assign(root)

        out = []
        for i, root in enumerate(roots):
            if i:
                out.append("")
            block, _ = self._render_horizontal_subtree(root, children_of, info_map)
            out.extend(block)
        return "\n".join(out)

    def _render_horizontal_subtree(self, node, children_of, info_map=None):
        """Render one horizontal subtree: node at left, children extend right."""
        children = children_of.get(node, [])
        text = self._temporal_node_text(node, info_map)
        if not children:
            return [text], 0

        parts = [self._render_horizontal_subtree(c, children_of, info_map)
                 for c in children]
        blocks = [block for block, _ in parts]
        roots = [root for _, root in parts]
        heights = [len(block) for block in blocks]

        # Connector rows are where each child's own line is placed.
        c_rows = [0]
        for i in range(1, len(children)):
            c_rows.append(c_rows[i - 1] + heights[i - 1] - roots[i - 1])
        y = [c_rows[i] - roots[i] for i in range(len(children))]
        min_y = min(y)
        max_y = max(y[i] + heights[i] - 1 for i in range(len(children)))
        rows = max_y - min_y + 1

        parent_row = c_rows[0] - min_y
        lines = [""] * rows
        for r in range(rows):
            lines[r] = text if r == parent_row else " " * len(text)

        text_w = len(text)
        for r in range(rows):
            abs_r = r + min_y
            if len(children) == 1:
                conn = "─── " if abs_r == c_rows[0] else "    "
                lines[r] = (text if r == parent_row else " " * text_w) + conn
            elif abs_r == c_rows[0]:
                lines[r] = text + "──┬── "
            elif abs_r == c_rows[-1]:
                lines[r] = " " * (text_w + 2) + "└── "
            elif abs_r in c_rows:
                lines[r] = " " * (text_w + 2) + "├── "
            elif c_rows[0] < abs_r < c_rows[-1]:
                lines[r] = " " * (text_w + 2) + "│   "
            else:
                lines[r] = " " * (text_w + 2) + "    "

        for i, block in enumerate(blocks):
            start = y[i] - min_y
            width = max((len(line) for line in block), default=0)
            for r, line in enumerate(block):
                lines[start + r] += line.ljust(width)

        return lines, parent_row

    def _show_temporal_network_dialog(self, text, title):
        """Show the plain-text tree in a scrollable, copyable dialog."""
        from PyQt5.QtWidgets import (
            QDialog, QVBoxLayout, QHBoxLayout, QTextEdit, QPushButton,
            QApplication,
        )
        from PyQt5.QtGui import QFontDatabase

        dlg = QDialog(self)
        dlg.setWindowTitle(title)
        dlg.resize(860, 620)
        layout = QVBoxLayout(dlg)

        edit = QTextEdit()
        edit.setReadOnly(True)
        edit.setLineWrapMode(QTextEdit.NoWrap)
        font = QFontDatabase.systemFont(QFontDatabase.FixedFont)
        font.setPointSize(11)
        edit.setFont(font)
        edit.setPlainText(text)
        layout.addWidget(edit, 1)

        btn_row = QHBoxLayout()
        btn_row.addStretch()
        btn_save_png = QPushButton(tr("lattice.temporal_save_png"))
        btn_save_png.clicked.connect(lambda: self._save_text_as_png(text))
        btn_copy = QPushButton(tr("table.copy"))
        btn_copy.clicked.connect(lambda: QApplication.clipboard().setText(text))
        btn_close = QPushButton(tr("dialog.close"))
        btn_close.clicked.connect(dlg.accept)
        btn_row.addWidget(btn_save_png)
        btn_row.addWidget(btn_copy)
        btn_row.addWidget(btn_close)
        layout.addLayout(btn_row)
        dlg.exec_()

    def _save_text_as_png(self, text):
        """Render the plain-text tree into a PNG image."""
        from PyQt5.QtWidgets import QTextEdit as _TextEdit
        from PyQt5.QtGui import QImage, QPainter, QFontDatabase
        from PyQt5.QtCore import QRectF

        path, _ = QFileDialog.getSaveFileName(
            self, tr("lattice.save_png"),
            temp_default_path("temporal_inclusion_network.png"),
            "PNG (*.png);;All Files (*)"
        )
        if not path:
            return

        edit = _TextEdit()
        font = QFontDatabase.systemFont(QFontDatabase.FixedFont)
        font.setPointSize(11)
        edit.setFont(font)
        edit.setLineWrapMode(_TextEdit.NoWrap)
        edit.setPlainText(text)
        doc = edit.document()
        size = doc.size()
        margin = 8
        w = max(1, int(size.width()) + margin * 2)
        h = max(1, int(size.height()) + margin * 2)
        image = QImage(w, h, QImage.Format_ARGB32)
        image.fill(Qt.white)

        painter = QPainter(image)
        try:
            doc.drawContents(painter, QRectF(margin, margin, size.width(), size.height()))
        finally:
            painter.end()

        if not image.save(path, "PNG"):
            QMessageBox.critical(
                self, tr("lattice.saved"),
                tr("lattice.save_permission_error", error="PNG save failed")
            )
            return
        QMessageBox.information(self, tr("lattice.saved"),
                                tr("dialog.saved_to", path=path))

    def _on_temporal_network(self):
        """Show a temporal inclusion network for the selected extracted set."""
        if not self._chord_entries:
            QMessageBox.information(self, tr("lattice.from_row_title"),
                                    tr("lattice.no_chord_msg"))
            return

        idx = self._chord_combo.currentIndex()
        if idx < 0 or idx >= len(self._chord_entries):
            return
        focus = tuple(sorted(self._chord_entries[idx]))
        focus_set = set(focus)

        nodes = {focus}
        for s in self._chord_entries:
            ts = tuple(sorted(s))
            if len(ts) >= 2 and set(ts).issubset(focus_set):
                nodes.add(ts)
        for key in self._lattice_node_full_info:
            if len(key) >= 2 and set(key).issubset(focus_set):
                nodes.add(key)
        if len(nodes) < 2:
            QMessageBox.information(self, tr("lattice.from_row_title"),
                                    tr("lattice.temporal_no_data"))
            return

        G, _levels = build_inclusion_graph(list(nodes))
        tree_text = self._build_temporal_tree_text(G)
        header = (f"Temporal Inclusion Network | Focus: {self._temporal_node_text(focus)} | "
                  f"{len(G.nodes())} sets, {len(G.edges())} relations")
        title = tr("lattice.btn_temporal_network")
        self._show_temporal_network_dialog(header + "\n\n" + tree_text, title)

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

    def _on_merge_from_score(self):
        """Merge from score and add selected sets to collections."""
        from src.core.merge_utils import MergeSelectorDialog, select_merge_items
        from collections import OrderedDict
        from music21 import chord as _chord
        from PyQt5.QtWidgets import QDialog
        mw = getattr(self, '_main_window', None)
        if not mw or not hasattr(mw, '_score') or not mw._score:
            QMessageBox.information(self, tr("forte.title"), tr("forte.no_chord_msg"))
            return
        dlg = MergeSelectorDialog(mw._score, self)
        if dlg.exec_() != QDialog.Accepted:
            return
        data, all_pcs, offset_data = dlg.get_result()
        # Clear old cached data
        self._chord_entries = []
        self._chord_combo.blockSignals(True)
        self._chord_combo.clear()
        self._chord_combo.blockSignals(False)
        self._collections_edit.clear()
        self._lattice_node_info = {}
        self._lattice_node_full_info = {}
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
        bar_items, indiv_items = [], []
        for bn in sorted(bar_detail):
            all_pb = set()
            for pn in bar_detail[bn]:
                pcs = bar_detail[bn][pn]
                orig_pcs = list(dict.fromkeys(data[pn][bn]))
                all_pb.update(pcs)
                if len(pcs) > 1:
                    indiv_items.append({"pcs": pcs, "orig_pcs": orig_pcs, "bar": bn, "part": f"{pn} [{', '.join(map(str, orig_pcs))}]", "forte": _chord.Chord(pcs).forteClass})
            merged = sorted(all_pb)
            if len(merged) > 1:
                bar_items.append({"pcs": merged, "bar": bn, "parts": ", ".join(f"{pn} [{', '.join(map(str, bar_detail[bn][pn]))}]" for pn in bar_detail[bn]), "forte": _chord.Chord(merged).forteClass})
        all_ordered = list(part_items)
        for bn in sorted(bar_detail):
            for _it in indiv_items:
                if _it["bar"] == bn:
                    all_ordered.append(_it)
            for _it in bar_items:
                if _it["bar"] == bn:
                    all_ordered.append(_it)
            for _it in offset_items:
                if _it["bar"] == bn:
                    all_ordered.append(_it)
        sel = select_merge_items(self, all_ordered, bar_items)
        if sel:
            sel_set = set(sel)
            out = []
            self._chord_entries = []
            self._chord_combo.blockSignals(True)
            self._chord_combo.clear()
            for _item in all_ordered:
                pc_key = " ".join(map(str, _item["pcs"]))
                if pc_key not in sel_set:
                    continue
                if 'part_name' in _item and 'bar_start' in _item:
                    _s = " ".join(map(str, _item.get('seq', _item['pcs'])))
                    out.append(f"# [Part Merge] {_item['part_name']} (Bars {_item['bar_start']}-{_item['bar_end']}): [{pc_key}] Forte: {_item['forte']}")
                    out.append(f"# Constituents: [{_s}]({_item['part_name']})")
                    out.append(_s)
                    self._chord_entries.append(_item["pcs"])
                    fkey = tuple(sorted(_item["pcs"]))
                    self._lattice_node_full_info.setdefault(fkey, [])
                    finfo = (_s, _item["forte"], f"Bars {_item['bar_start']}-{_item['bar_end']} ({_item['part_name']} merged)")
                    if finfo not in self._lattice_node_full_info[fkey]:
                        self._lattice_node_full_info[fkey].append(finfo)
                    self._chord_combo.addItem(f"[Part Merge] {_item['part_name']}: [{_s}] ({_item['forte']})")
                elif 'offset' in _item:
                    out.append(f"# [Offset Merge] Bar {_item['bar']} offset {_item['offset']}: [{pc_key}] Forte: {_item['forte']} ({_item['offset_pcs']})")
                    out.append(pc_key)
                    self._chord_entries.append(_item["pcs"])
                    fkey = tuple(sorted(_item["pcs"]))
                    self._lattice_node_full_info.setdefault(fkey, [])
                    finfo = (pc_key, _item["forte"], f"Bar {_item['bar']} Offset {_item['offset']} (Offset merged)")
                    if finfo not in self._lattice_node_full_info[fkey]:
                        self._lattice_node_full_info[fkey].append(finfo)
                    self._chord_combo.addItem(f"[Offset Merge] {_item['bar']} offset {_item['offset']}: [{pc_key}] ({_item.get('offset_pcs','')})")
                elif 'parts' in _item:
                    _s = " ".join(map(str, _item.get('orig_seq', _item["pcs"])))
                    out.append(f"# [Bar Merge] Bar {_item['bar']}: [{_s}] Forte: {_item['forte']} ({_item.get('parts','')})")
                    out.append(pc_key)
                    self._chord_entries.append(_item["pcs"])
                    fkey = tuple(sorted(_item["pcs"]))
                    self._lattice_node_full_info.setdefault(fkey, [])
                    finfo = (_s, _item["forte"], f"Bar {_item['bar']} (Bar merged)")
                    if finfo not in self._lattice_node_full_info[fkey]:
                        self._lattice_node_full_info[fkey].append(finfo)
                    self._chord_combo.addItem(f"[Bar Merge] {_item['bar']}: [{_s}] ({_item.get('parts','')})")
                else:
                    _s = " ".join(map(str, _item.get('orig_pcs', _item["pcs"])))
                    out.append(f"# [Chord] Bar {_item['bar']}: [{_s}] Forte: {_item['forte']} ({_item.get('part','')})")
                    out.append(pc_key)
                    self._chord_entries.append(_item["pcs"])
                    fkey = tuple(sorted(_item["pcs"]))
                    self._lattice_node_full_info.setdefault(fkey, [])
                    finfo = (_s, _item["forte"], f"Bar {_item['bar']} ({_item.get('part','')})")
                    if finfo not in self._lattice_node_full_info[fkey]:
                        self._lattice_node_full_info[fkey].append(finfo)
                    self._chord_combo.addItem(f"[Chord] {_item['bar']}: [{_s}] ({_item.get('part','')})")
            self._chord_combo.blockSignals(False)
            self._chord_combo.setEnabled(True)
            if self._chord_entries:
                self._chord_combo.setCurrentIndex(-1)
                self._chord_combo.setCurrentIndex(0)
            self._btn_chord_relations.setEnabled(True)
            self._btn_temporal_network.setEnabled(True)
            self._btn_save.setEnabled(True)
            self._collections_edit.setText("\n".join(out))
