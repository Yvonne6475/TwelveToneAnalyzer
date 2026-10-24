import os
import tempfile
import zipfile
import colorsys
import re
# 强制指定使用 Tkinter 交互后端，确保能够弹出交互式窗口
# (Only when running standalone; when imported from the PyQt app the
#  main process already chooses its own backend.)
import sys as _sys
import matplotlib

if __name__ == "__main__":
    matplotlib.use('TkAgg')

import tkinter as tk
from tkinter import filedialog, messagebox, simpledialog
import matplotlib.pyplot as plt
from matplotlib.widgets import CheckButtons, Slider, RadioButtons, Button, TextBox, RectangleSelector
from matplotlib.colors import ListedColormap, BoundaryNorm
from matplotlib.collections import PatchCollection
import numpy as np
import matplotlib.patches as patches

# Configure Matplotlib global font and Unicode settings (采用学术推荐的无衬线体)
plt.rcParams['font.sans-serif'] = ['Arial', 'DejaVu Sans', 'Helvetica']
plt.rcParams['axes.unicode_minus'] = False
plt.rcParams['figure.dpi'] = 120
if _sys.platform == 'darwin':
    plt.rcParams['figure.dpi'] = 120
    plt.rcParams['savefig.dpi'] = 120

# Configure temporary cache directory for music21
temp_dir = os.path.join(tempfile.gettempdir(), "music21")
os.makedirs(temp_dir, exist_ok=True)

import music21 as m21

env = m21.environment.UserSettings()
env["directoryScratch"] = temp_dir


def generate_high_contrast_palette(num_colors=256):
    """
    Generate a high-contrast palette using golden ratio hue distribution.
    Fixed saturation and lightness so every consecutive index has a
    perceptibly different hue (golden ratio advances hue ~222° per step).
    """
    colors = [[1.0, 1.0, 1.0, 1.0]]  # Index 0 is reserved for background (white)
    golden_ratio_conjugate = 0.618033988749895
    h = 0.1  # Starting hue

    for i in range(1, num_colors):
        h = (h + golden_ratio_conjugate) % 1.0
        s = 0.80  # fixed saturation
        l = 0.52  # fixed lightness

        r, g, b = colorsys.hls_to_rgb(h, l, s)
        colors.append([r, g, b, 1.0])

    return np.array(colors)


def fast_pitch_class_info(pcs):
    """Fast pitch-class set analysis — O(1) lookup in the pre-computed
    Forte set-class database, with a music21 fallback for robustness."""
    if not pcs:
        return "Empty", "[]", "[0 0 0 0 0 0]"
    key = tuple(sorted(set(pcs)))
    try:
        from src.core.forte_db import fast_forte_info
        return fast_forte_info(key)
    except Exception:
        c = m21.chord.Chord(list(key))
        forte = c.forteClass if c.forteClass else "N/A"
        prime = str(c.primeForm)
        iv = str(c.intervalVector)
        return forte, prime, iv


def format_corpus_two_lines(text):

    """Return only the file text for the TextBox (no "Corpus:" header)."""
    if not text:
        return ""

    max_len_line = 45
    if len(text) <= max_len_line:
        return text

    mid = min(len(text), max_len_line)
    best_split = mid
    for i in range(mid - 3, min(len(text), mid + 5)):
        if 0 <= i < len(text) and text[i] in ['_', ' ', '-']:
            best_split = i + 1
            break
    return f"{text[:best_split].strip()}\n{text[best_split:].strip()}"




class _EdgeOnlyRectangleSelector(RectangleSelector):
    """RectangleSelector variant with a small center handle.

    Edge/corner resize has priority; the center handle is kept small so
    it only moves the selection when grabbed directly or when the
    default move modifier (space) is held.
    """
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Small center grab radius (in pixels): avoids stealing N/S edge
        # clicks when the rectangle is short.
        self._center_grab_range = max(3, self.grab_range // 2)
        # Shrink the visible center square and all edge/corner handles.
        for handle in (self._center_handle, self._edge_handles, self._corner_handles):
            for artist in getattr(handle, 'artists', []):
                try:
                    artist.set_markersize(4.0)
                except Exception:
                    pass

    def _set_active_handle(self, event):
        # Note: event.xdata/ydata in data coordinates, event.x/y in pixels
        c_idx, c_dist = self._corner_handles.closest(event.x, event.y)
        e_idx, e_dist = self._edge_handles.closest(event.x, event.y)
        m_idx, m_dist = self._center_handle.closest(event.x, event.y)

        # move modifier (space by default) forces a whole-rect move
        if 'move' in self._state:
            self._active_handle = 'C'
        elif m_dist < self._center_grab_range:
            self._active_handle = 'C'
        elif c_dist > self.grab_range and e_dist > self.grab_range:
            # Not close to any handles
            if self.drag_from_anywhere and self._contains(event):
                self._active_handle = 'C'
            else:
                self._active_handle = None
                return
        elif c_dist < e_dist:
            self._active_handle = self._corner_order[c_idx]
        else:
            self._active_handle = self._edge_order[e_idx]


class InteractiveDynamicSetExplorer:
    def __init__(self, score_path=None, score=None):
        # Initialize hidden Tkinter root window for dialog boxes
        self.root = tk.Tk()
        self.root.withdraw()
        self.root.attributes('-topmost', True)
        # Improve High-DPI rendering on Retina / 4K displays
        try:
            self.root.tk.call('tk', 'scaling', 2.0)
        except Exception:
            pass

        # Generate pre-calculated high-contrast palette
        self.palette = generate_high_contrast_palette(num_colors=2048)

        # Predefined voice colors
        self.voice_colors = ['#D62728', '#1F77B4', '#2CA02C', '#FF7F0E', '#9467BD', '#17BECF', '#8C564B', '#E377C2']
        self.voice_legend = {}

        if score is not None:
            # Use an already-parsed music21 Score object
            self.score = score
            self.xml_path = score_path or getattr(score, 'metadata', None) and getattr(score.metadata, 'title', None) or "Loaded Score"
        elif score_path:
            # Load directly from local file
            target_path = score_path
            is_local = os.path.exists(target_path)
            self._load_score_data(target_path, is_local=is_local)
        else:
            # Initial prompt asking for corpus name or local file path
            target_path, is_local = self._get_initial_score_input()
            self._load_score_data(target_path, is_local=is_local)

        self._parse_score()
        self._recompute_data_grid()
        self._init_ui()

    def _get_initial_score_input(self):
        """Prompt user at startup for music21 corpus name or local file path."""
        user_input = simpledialog.askstring(
            "Select Score",
            "Please enter music21 corpus path (e.g. 'bach/bwv846') or local file path:\n(Leave empty to browse local file)",
            parent=self.root
        )

        if user_input and user_input.strip():
            path = user_input.strip().strip('"').strip("'")

            if os.path.exists(path):
                return path, True

            try:
                m21.corpus.parse(path)
                return path, False
            except Exception:
                messagebox.showwarning("Parse Warning", f"Could not find path or corpus '{path}'. Opening file picker.")

        file_path = filedialog.askopenfilename(
            title="Choose Local Music Score File",
            filetypes=[
                ("Supported Score Files", "*.xml *.mxl *.musicxml *.mscz *.mid *.midi"),
                ("MuseScore Files", "*.mscz"),
                ("MusicXML Files", "*.xml *.mxl *.musicxml"),
                ("MIDI Files", "*.mid *.midi"),
                ("All Files", "*.*")
            ]
        )
        if file_path:
            return file_path, True

        default_path = "beethoven/opus18no1/movement2.mxl"
        messagebox.showinfo("Default Loaded", f"No valid input provided. Loading default corpus: {default_path}")
        return default_path, False

    def _load_score_data(self, target, is_local=False):
        """Load score data either from local file path or music21 corpus with .mscz support."""
        self.xml_path = target
        if is_local:
            if target.lower().endswith('.mscz'):
                temp_extract_dir = os.path.join(tempfile.gettempdir(), "mscz_extracted")
                os.makedirs(temp_extract_dir, exist_ok=True)

                with zipfile.ZipFile(target, 'r') as zip_ref:
                    xml_files = [f for f in zip_ref.namelist() if f.endswith('.mxl') or f.endswith('.xml')]
                    if xml_files:
                        extracted_path = zip_ref.extract(xml_files[0], temp_extract_dir)
                        self.score = m21.converter.parse(extracted_path)
                    else:
                        raise ValueError("No valid XML content found inside the .mscz archive.")
            else:
                self.score = m21.converter.parse(target)
        else:
            self.score = m21.corpus.parse(target)

    def _parse_score(self):
        """Parse note and chord events from the score into time-series data, capturing voice/part mapping."""
        print("Parsing score data...")
        self.total_length = float(self.score.highestTime)

        starts_list = []
        ends_list = []
        pcs_list = []
        event_voice_ids = []
        self.piano_roll_notes = []  # List of tuples: (start, dur, pitch, voice_id)
        self.voice_legend = {}

        if hasattr(self.score, 'hasPartLikeTree') and self.score.hasPartLikeTree():
            parts = self.score.parts
        elif hasattr(self.score, 'parts') and len(self.score.parts) > 0:
            parts = self.score.parts
        else:
            parts = [self.score]

        # Phase 1: collect all events across all parts with their temporal info
        raw_events = []  # (abs_start, part_idx, part_name, el, dur)

        for part_idx, part in enumerate(parts):
            part_name = getattr(part, 'partName', None)
            if not part_name:
                part_name = f"Part {part_idx + 1}"

            for el in part.recurse().getElementsByClass(["Note", "Chord"]):
                abs_start = float(el.getOffsetInHierarchy(self.score))
                dur = float(el.quarterLength)
                raw_events.append((abs_start, part_idx, part_name, el, dur))

        # Sort: by offset ascending; for same offset, by highest pitch descending
        # (top to bottom, matching voice hierarchy); same-highest-pitch uses part index.
        def _event_sort_key(e):
            offset, part_idx, _, el, _ = e
            if isinstance(el, m21.chord.Chord):
                highest = max(p.midi for p in el.pitches)
            else:
                highest = el.pitch.midi
            return (offset, -highest, part_idx)

        raw_events.sort(key=_event_sort_key)

        # Phase 2: populate all lists in the sorted order
        for abs_start, part_idx, part_name, el, dur in raw_events:
            abs_end = abs_start + dur
            voice_id = part_idx

            event_voice_ids.append(voice_id)

            if voice_id not in self.voice_legend:
                color_idx = len(self.voice_legend) % len(self.voice_colors)
                self.voice_legend[voice_id] = {
                    "name": f"{part_name} (V:{voice_id})",
                    "color": self.voice_colors[color_idx],
                    "color_idx": color_idx
                }

            if isinstance(el, m21.chord.Chord):
                sorted_pitches = sorted(el.pitches, key=lambda p: p.midi, reverse=True)
                pcs = tuple(p.pitchClass for p in sorted_pitches)

                for p in sorted_pitches:
                    self.piano_roll_notes.append((abs_start, dur, p.midi, voice_id))
            else:
                pcs = (el.pitch.pitchClass,)
                self.piano_roll_notes.append((abs_start, dur, el.pitch.midi, voice_id))

            starts_list.append(abs_start)
            ends_list.append(abs_end)
            pcs_list.append(pcs)

        self.active_voice_ids = set(self.voice_legend.keys())  # all checked by default
        # Keep the full unfiltered data plus an event voice id per event,
        # so Refresh can rebuild filtered arrays without re-parsing.
        self.full_starts_arr = np.array(starts_list)
        self.full_ends_arr = np.array(ends_list)
        self.full_pcs_arr = pcs_list
        self.full_piano_roll_notes = list(self.piano_roll_notes)
        self.event_voice_ids = list(event_voice_ids)
        # Working copies that honor the voice filter
        self.starts_arr = np.array(starts_list)
        self.ends_arr = np.array(ends_list)
        self.pcs_arr = pcs_list

        # Flat PC arrays: one row per pitch-class for fast numpy masking
        _fs, _fe, _fp = [], [], []
        for i, pc_tuple in enumerate(pcs_list):
            s = starts_list[i]
            e = ends_list[i]
            for pc in pc_tuple:
                _fs.append(s); _fe.append(e); _fp.append(pc)
        self._flat_starts = np.array(_fs, dtype=np.float64)
        self._flat_ends   = np.array(_fe, dtype=np.float64)
        self._flat_pcs    = np.array(_fp, dtype=np.int32)

        if self.piano_roll_notes:
            all_midis = [n[2] for n in self.piano_roll_notes]
            self.min_midi = max(21, min(all_midis) - 2)
            self.max_midi = min(108, max(all_midis) + 2)
        else:
            self.min_midi, self.max_midi = 36, 84

        if self.total_length > 800:
            self.offset_step = 2.0
        else:
            self.offset_step = 1.0

        self.max_scale_offset = max(2.0, self.total_length / 2.0)
        self.selected_offset_idx = 0
        self.selected_scale_idx = 0
        self.cardinality_mask = set(range(1, 13))
        self._forte_cache = {}
        self.pcs_cache = {}
        self._forte_cache = {}

        self.custom_2d_selection = None
        self._pan_step_active = False
        self.active_tool = 'Browse'
        self.selection_enabled = False

    # ---------- Fast redraw (blit) helpers ----------
    def _init_blit(self):
        """Set up background caching for fast partial redraws.

        Static content (piano roll, pcolormesh, axes spines/labels) is
        captured once into a cached background.  Changing artists (crosshair,
        window patch, info text, voice panel) are repainted on top with blit.

        IMPORTANT: the cached background must NOT contain any dynamic artist.
        _capture_background hides the entire dynamic layer before capturing.
        """
        # Preserve artists that were already registered by _update_text_info /
        # _draw_voice_panel during _init_ui; do NOT reset the lists here.
        if not hasattr(self, '_blit_artists'):
            self._blit_artists = []
        if not hasattr(self, '_voice_artists'):
            self._voice_artists = []
        self._bg = None
        self._capturing_bg = False
        # adopt artists created before _init_blit ran (crosshair, window patch,
        # body text, voice panel) into the dynamic layer
        if hasattr(self, 'crosshair') and self.crosshair is not None:
            self._add_blit_artist(self.crosshair)
        if getattr(self, 'window_patch', None) is not None:
            self._add_blit_artist(self.window_patch)
        if getattr(self, '_text_artist', None) is not None:
            self._add_blit_artist(self._text_artist)
        # Voice-panel artists live in the background, not the dynamic layer.

    def _set_dynamic_visible(self, visible):
        for art in getattr(self, '_blit_artists', []):
            try:
                art.set_visible(visible)
            except Exception:
                pass

    def _capture_background(self, redraw_dynamic=True):
        """Capture a background snapshot containing ONLY static content."""
        canvas = self.fig.canvas
        fig = self.fig
        self._set_dynamic_visible(False)
        self._capturing_bg = True
        try:
            fig.canvas.draw()
            self._bg = canvas.copy_from_bbox(fig.bbox)
        except Exception:
            self._bg = None
        finally:
            self._capturing_bg = False
            self._set_dynamic_visible(True)
        if self._bg is not None and redraw_dynamic:
            canvas.restore_region(self._bg)
            for art in getattr(self, '_blit_artists', []):
                fig.draw_artist(art)
            canvas.blit(fig.bbox)
            try:
                canvas.flush_events()
            except Exception:
                pass

    def _add_blit_artist(self, art):
        art.set_animated(True)
        lst = getattr(self, '_blit_artists', None)
        if lst is None:
            self._blit_artists = []
            lst = self._blit_artists
        if art not in lst:
            lst.append(art)

    def _remove_blit_artist(self, art):
        lst = getattr(self, '_blit_artists', None)
        if lst and art in lst:
            lst.remove(art)

    def _replace_voice_artists(self, artists):
        """Voice-panel artists are static — painted into the background.
        They only change on voice toggles, which recaptures the bg."""
        self._voice_artists = artists

    def _fast_refresh(self):
        """Blit-redraw only the dynamic layer onto a pre-cached background."""
        canvas = self.fig.canvas
        fig = self.fig
        if getattr(self, '_bg', None) is None:
            self._capture_background()
            if getattr(self, '_bg', None) is None:
                fig.canvas.draw_idle()
                return
        try:
            canvas.restore_region(self._bg)
            for art in getattr(self, '_blit_artists', []):
                fig.draw_artist(art)
            canvas.blit(fig.bbox)
            try:
                canvas.flush_events()
            except Exception:
                pass
        except Exception:
            fig.canvas.draw_idle()

    def _set_scrollbar_no_draw(self, val):
        """Move the pan scrollbar without triggering a full-canvas draw_idle
        (Slider.set_val calls draw_idle internally when drawon is True)."""
        try:
            self.scrollbar.drawon = False
        except Exception:
            pass
        self.scrollbar.eventson = False
        self.scrollbar.set_val(val)
        self.scrollbar.eventson = True
        try:
            self.scrollbar.drawon = True
        except Exception:
            pass

    def _on_key_press(self, event):
        """Handle arrow key stepping for Pan View."""
        if event.key in ('left', 'right') and getattr(self, '_pan_step_active', False):
            step = 0.1
            delta = -step if event.key == 'left' else step
            new_val = min(max(self.scrollbar.val + delta, 
                              self.scrollbar.valmin), 
                          self.scrollbar.valmax)
            if abs(new_val - self.scrollbar.val) > 1e-9:
                self.scrollbar.eventson = False
                self.scrollbar.set_val(new_val)
                self.scrollbar.eventson = True
                self._on_scroll_pan(new_val)
            event.guiEvent = True  # prevent propagation

    def _get_set_info(self, pcs):
        pcs_tuple = tuple(dict.fromkeys(pcs))
        cache_key = tuple(sorted(pcs_tuple))

        if cache_key not in self.pcs_cache:
            if not cache_key:
                self.pcs_cache[cache_key] = {
                    'forte': 'Empty',
                    'prime': '[]',
                    'iv': '[0 0 0 0 0 0]'
                }
            else:
                forte, prime, iv = fast_pitch_class_info(cache_key)
                self.pcs_cache[cache_key] = {
                    'forte': forte,
                    'prime': prime,
                    'iv': iv
                }

        return pcs_tuple, self.pcs_cache[cache_key]

    def _get_forte_color_index(self, forte_name):
        # Guaranteed unique-per-Forte: sequential allocation up to palette size.
        # If palette exhausted, falls back to deterministic hash (same Forte always same color).
        if not forte_name or forte_name in ["Empty", "N/A"]:
            return 0
        if not hasattr(self, '_forte_color_map'):
            self._forte_color_map = {}
            self._forte_next = 1
        idx = self._forte_color_map.get(forte_name)
        if idx is not None:
            return idx
        max_p = len(self.palette) - 1
        if self._forte_next <= max_p:
            idx = self._forte_next
            self._forte_next += 1
        else:
            # Palette exhausted → hash-based fallback (no collisions in practice with 2048 slots)
            idx = 1 + (hash(forte_name) % max_p)
        self._forte_color_map[forte_name] = idx
        return idx

    def _recompute_data_grid(self):
        event_boundaries = sorted(list(set(self.starts_arr).union(set(self.ends_arr))))
        if 0.0 not in event_boundaries:
            event_boundaries.insert(0, 0.0)
        if self.total_length not in event_boundaries:
            event_boundaries.append(self.total_length)

        self.offset_boundaries = np.array(event_boundaries)
        self.offset_points = self.offset_boundaries[:-1]
        self.num_points = len(self.offset_points)

        self.scales = np.arange(self.offset_step, self.max_scale_offset + self.offset_step, self.offset_step)
        self.num_scales = len(self.scales)

        # Pre-sort flat arrays by start time for searchsorted
        _fs = self._flat_starts
        _fe = self._flat_ends
        _fp = self._flat_pcs
        _sort_idx = np.argsort(_fs, kind='stable')
        _fs_sorted = _fs[_sort_idx]
        _fe_sorted = _fe[_sort_idx]
        _fp_sorted = _fp[_sort_idx]

        self.data_grid = {}
        scales_arr = self.scales
        ob = self.offset_boundaries
        # Pre-allocate output arrays for the matrix
        self.matrix_display = np.zeros((self.num_scales, self.num_points), dtype=int)

        for o_idx in range(self.num_points):
            start_offset = ob[o_idx]
            end_offsets = start_offset + scales_arr

            i_ends = np.searchsorted(_fs_sorted, end_offsets, side='left')

            for s_idx, (i_end, scale_offset) in enumerate(zip(i_ends, scales_arr)):
                if i_end == 0:
                    cell = {
                        "pcs": [], "card": 0,
                        "forte": "Empty", "prime": "", "iv": "",
                        "start_offset": start_offset,
                        "end_offset": min(self.total_length, start_offset + scale_offset)
                    }
                    self.data_grid[(s_idx, o_idx)] = cell
                    continue

                _cand_end = _fe_sorted[:i_end]
                _cand_pcs = _fp_sorted[:i_end]
                _sub = _cand_end > start_offset
                if np.any(_sub):
                    # Use np.unique for fast dedup + sort
                    pcs_arr = np.unique(_cand_pcs[_sub])
                    pcs_list = pcs_arr.tolist()
                else:
                    pcs_list = []

                card = len(pcs_list)
                cell = {
                    "pcs": pcs_list, "card": card,
                    "start_offset": start_offset,
                    "end_offset": min(self.total_length, start_offset + scale_offset)
                }
                if card > 0:
                    pcs_key = tuple(pcs_list)
                    cached = self._forte_cache.get(pcs_key)
                    if cached:
                        forte, prime, iv = cached
                    else:
                        forte, prime, iv = fast_pitch_class_info(pcs_list)
                        self._forte_cache[pcs_key] = (forte, prime, iv)
                    cell["forte"] = forte
                    cell["prime"] = prime
                    cell["iv"] = iv
                    if card in self.cardinality_mask and forte not in ["Empty", "N/A"]:
                        self.matrix_display[s_idx, o_idx] = self._get_forte_color_index(forte)
                else:
                    cell["forte"] = "Empty"
                    cell["prime"] = ""
                    cell["iv"] = ""
                self.data_grid[(s_idx, o_idx)] = cell

    def _update_matrix(self):
        # Matrix is already populated in _recompute_data_grid; this method
        # re-applies cardinality filtering for toggle changes without recomputing Forte.
        self.matrix_display.fill(0)
        for (s_idx, o_idx), data in self.data_grid.items():
            card = data.get("card", 0)
            if card in self.cardinality_mask and card > 0:
                forte = data.get("forte", "Empty")
                if forte not in ["Empty", "N/A"]:
                    self.matrix_display[s_idx, o_idx] = self._get_forte_color_index(forte)

    def _init_ui(self):
        # Figure DPI: 120 gives noticeably sharper text but keeps the
        # window close to standard screen sizes; on Retina macOS the Tk
        # scaling makes it crisp.
        # 画布尺寸加大、右栏比例提高，确保文本/控件全部完整显示
        self.fig = plt.figure(figsize=(19, 18), dpi=120)


        self.fig.suptitle("Dynamic Multi-Scale Setscape Explorer ", fontsize=13, fontweight='bold',
                          x=0.5, ha='center')

        # 主 gridspec: 左(主图) | 右(信息+控件)
        gs_main = self.fig.add_gridspec(1, 3, width_ratios=[12.0, 0.8, 17.0], wspace=0.02)

        # 左列 5 行: scape / scrollbar / piano / slider_max / slider_step
        gs_left = gs_main[0, 0].subgridspec(
            5, 1, height_ratios=[3.0, 0.18, 3.2, 0.14, 0.14], hspace=0.55
        )
        self.ax_scape = self.fig.add_subplot(gs_left[0])
        self.ax_scrollbar = self.fig.add_subplot(gs_left[1])
        self.ax_piano = self.fig.add_subplot(gs_left[2])
        self.ax_slider_max_scale = self.fig.add_subplot(gs_left[3])
        self.ax_slider_step = self.fig.add_subplot(gs_left[4])

        # 右列 4 行: 声部信息框最大化，底部控件推到最底下
        gs_right = gs_main[0, 2].subgridspec(
            4, 1, height_ratios=[8.0, 2.5, 4.0, 0.3], hspace=0.15
        )
        self.ax_text = self.fig.add_subplot(gs_right[0])
        self.ax_voices = self.fig.add_subplot(gs_right[1])

        # 控制区: 左 [Cardinality 复选] | 右 [Corpus / Tools / Buttons]
        gs_controls = gs_right[2].subgridspec(1, 2, width_ratios=[0.32, 0.68], wspace=0.15)
        self.ax_check = self.fig.add_subplot(gs_controls[0])

        gs_right_inner = gs_controls[1].subgridspec(
            3, 1, height_ratios=[1.6, 1.8, 0.9], hspace=0.10
        )
        self.ax_textbox = self.fig.add_subplot(gs_right_inner[0])
        self.ax_tools = self.fig.add_subplot(gs_right_inner[1])

        gs_btns_sub = gs_right_inner[2].subgridspec(1, 3, wspace=0.30, hspace=0.0)
        self.ax_btn_reset = self.fig.add_subplot(gs_btns_sub[0])
        self.ax_btn_refresh = self.fig.add_subplot(gs_btns_sub[1])
        self.ax_btn_file = self.fig.add_subplot(gs_btns_sub[2])

        # 预留空行避免压到边缘
        self.ax_spacer = self.fig.add_subplot(gs_right[3])
        self.ax_spacer.set_xticks([])
        self.ax_spacer.set_yticks([])
        for s in self.ax_spacer.spines.values():
            s.set_visible(False)

        self._update_matrix()

        self.custom_cmap = ListedColormap(self.palette)
        self.custom_norm = BoundaryNorm(np.arange(-0.5, len(self.palette) + 0.5, 1), self.custom_cmap.N)

        scale_boundaries = np.append(self.scales - self.offset_step / 2, self.scales[-1] + self.offset_step / 2)
        X, Y = np.meshgrid(self.offset_boundaries, scale_boundaries)

        self.quad_mesh = self.ax_scape.pcolormesh(
            X, Y, self.matrix_display,
            cmap=self.custom_cmap,
            norm=self.custom_norm,
            shading='flat'
        )
        self.ax_scape.set_ylabel("Window Size / Scale (Offset)", fontsize=10)
        self.ax_scape.tick_params(axis="both", labelsize=8)
        self.ax_scape.set_xlabel("Actual Offset Position (Quarter Notes)", fontsize=10)
        self.ax_scape.tick_params(axis="both", labelsize=8)

        init_offset = self.offset_points[0]
        init_scale = self.scales[0]
        self.crosshair, = self.ax_scape.plot([init_offset], [init_scale], 'r+', markersize=14, markeredgewidth=2)

        self.slider_max_scale = Slider(
            ax=self.ax_slider_max_scale, label='Window ',
            valmin=2.0, valmax=self.total_length, valinit=self.max_scale_offset, valstep=1.0, dragging=False
        )
        self.slider_max_scale.on_changed(self._on_slider_release)
        self.slider_max_scale.label.set_fontsize(6)

        self.slider_step = Slider(
            ax=self.ax_slider_step,
            label='Step ',
            valmin=0.1,
            valmax=16.0,
            valinit=self.offset_step,
            valstep=0.1
        )
        self.slider_step.label.set_fontsize(6)

        self.scrollbar = Slider(
            ax=self.ax_scrollbar, label='Pan ',
            valmin=0.0, valmax=self.total_length, valinit=self.total_length / 2.0,
            valstep=0.1, color='lightgray', valfmt='%0.1f'
        )
        self.scrollbar.on_changed(self._on_scroll_pan)
        self.scrollbar.label.set_fontsize(6)

        labels = [str(i) for i in range(1, 13)]
        # Add a master "All" checkbox at the top of the list
        self.check_box = CheckButtons(self.ax_check, ["All"] + labels, [True] * 13)
        self.check_box.on_clicked(self._on_card_toggle)

        # Reduce font size and increase line spacing for cardinality labels
        # Reduce font size and increase line spacing for cardinality labels
        if hasattr(self.check_box, 'labels'):
            for i, lbl in enumerate(self.check_box.labels):
                lbl.set_fontsize(6)
        n_labels = len(self.check_box.labels)  # 13 = All + 1..12
        self.ax_check.set_ylim(-1.5, n_labels + 1.5)
        # 格式化文本 — "Corpus:" 标题独立放置在 ax_textbox 上方，框内仅显示文件名
        base_name = os.path.basename(self.xml_path)
        corpus_display_text = format_corpus_two_lines(base_name)

        # 关闭坐标轴显示，用 set_title 作为 "Corpus:" 标签
        self.ax_textbox.set_xticks([])
        self.ax_textbox.set_yticks([])
        for s in self.ax_textbox.spines.values():
            s.set_visible(False)
        self.ax_textbox.set_title('Corpus:', fontsize=6, loc='left', pad=3)

        self.textbox_corpus = TextBox(self.ax_textbox, '', initial=corpus_display_text)

        if hasattr(self.textbox_corpus, 'text_disp'):
            self.textbox_corpus.text_disp.set_fontsize(6.0)
            self.textbox_corpus.text_disp.set_ha('left')
            self.textbox_corpus.text_disp.set_va('top')
            self.textbox_corpus.text_disp.set_position((0.02, 0.95))
            self.textbox_corpus.text_disp.set_linespacing(1.1)

        self.textbox_corpus.on_submit(self._on_corpus_submit)

        self.radio_tools = RadioButtons(
            self.ax_tools,
            ('Browse', 'Set Select', 'Zoom In (+)', 'Zoom Out (-)'),
            active=0
        )

        if hasattr(self.radio_tools, 'circles') and hasattr(self.radio_tools, 'labels'):
            n_options = len(self.radio_tools.labels)
            # 圆点大一些靠左，文字靠右对齐，确保点击文字区域也能命中
            # 内置 RadioButtons 的 on_clicked 只检测 circles 命中，
            # 所以我们额外连一个 button_press_event 做最近邻匹配
            new_ys = np.array([0.78, 0.58, 0.38, 0.18])
            for i, (circle, label) in enumerate(zip(self.radio_tools.circles, self.radio_tools.labels)):
                y_pos = new_ys[i]
                circle.set_center((0.16, y_pos))
                circle.set_radius(0.06)
                label.set_position((0.30, y_pos))
                label.set_fontsize(4.0)
                label.set_horizontalalignment('left')
                label.set_verticalalignment('center')

        # 扩展点击区域：当点击 ax_tools 内但没命中 circles 时，做最近邻匹配
        self._radio_tools_pick_cid = self.fig.canvas.mpl_connect(
            'button_press_event', self._on_radio_tools_extended_click
        )
        self.radio_tools.on_clicked(self._on_tool_change)

        self.btn_reset = Button(self.ax_btn_reset, 'Reset')
        self.btn_reset.label.set_fontsize(7)
        self.btn_reset.on_clicked(self._on_reset_view)

        # Refresh 刷新按钮
        self.btn_refresh = Button(self.ax_btn_refresh, 'Refresh', color='#E1D5E7', hovercolor='#D4B1D0')
        self.btn_refresh.label.set_fontsize(7)
        self.btn_refresh.on_clicked(self._on_refresh)

        self.btn_file = Button(self.ax_btn_file, 'Open File', color='lightblue', hovercolor='skyblue')
        self.btn_file.label.set_fontsize(7)
        self.btn_file.on_clicked(self._on_select_file)

        # Matplotlib Slider handles click-to-jump itself; valstep snaps drags to 0.1
        self.fig.canvas.mpl_connect('button_press_event', self._on_click)
        self.fig.canvas.mpl_connect('key_press_event', self._on_key_press)

        self._draw_base_piano_roll()

        self.rect_selector = _EdgeOnlyRectangleSelector(
            self.ax_piano,
            self._on_piano_roll_2d_select,
            useblit=True,
            props=dict(alpha=0.3, facecolor='red', edgecolor='red', linewidth=1.5),
            interactive=True,
            drag_from_anywhere=False,
            spancoords='data'
        )
        self.rect_selector.set_active(False)

        self._update_window_overlay()
        self._update_text_info()
        plt.tight_layout()
        # Set up fast (blit) redraw: Dynamically-changing artists were created
        # by _update_window_overlay / _update_text_info above.
        self._init_blit()
        # Background will be captured on first click (after window is shown and
        # layout is stable; capturing before plt.show() gives wrong dimensions).
        plt.show()

    def _remove_window_overlay(self):
        if hasattr(self, 'window_patch') and self.window_patch is not None:
            if self.window_patch in self.ax_piano.patches:
                self.window_patch.remove()
            self.window_patch = None

    def _clear_custom_2d_selection(self):
        self.custom_2d_selection = None
        if hasattr(self, 'rect_selector') and self.rect_selector is not None:
            self.rect_selector.set_visible(False)

    def _on_radio_tools_extended_click(self, event):
        """Extended click handler: any click in ax_tools triggers radio selection
        by nearest y-distance to labels (avoids double-fire by checking if click
        is far from all circles)."""
        if event.inaxes != self.ax_tools:
            return
        labels = self.radio_tools.labels
        circles = self.radio_tools.circles
        if not labels or not circles:
            return
        ax_x, ax_y = event.xdata, event.ydata
        # Check if click is near any circle (within 2x radius) — if so, skip
        # (built-in RadioButtons already handles it)
        for circle in circles:
            cx, cy = circle.center
            r = circle.radius
            if (ax_x - cx) ** 2 + (ax_y - cy) ** 2 <= r ** 2:
                return
        # Get label y-positions (already set in axes coords via set_position)
        label_ys = [(label.get_position()[1], i) for i, label in enumerate(labels)]
        if not label_ys:
            return
        nearest_idx = min(label_ys, key=lambda t: abs(t[0] - ax_y))[1]
        self.radio_tools.set_active(nearest_idx)

    def _on_tool_change(self, label):
        self.active_tool = label

        if label == 'Set Select':
            self.selection_enabled = True
            self.rect_selector.set_active(True)
        else:
            self.selection_enabled = False
            self.rect_selector.set_active(False)
            self._clear_custom_2d_selection()

        self._update_window_overlay()
        self._update_text_info()
        self._capture_background(redraw_dynamic=True)

    def _analyze_custom_2d_range(self, start_offset, end_offset, min_pitch, max_pitch):
        pcs_sequence = []
        voice_ids_in = set()
        voice_pcs = {}  # voice_id -> ordered list of pcs in selection
        for note_tuple in self.piano_roll_notes:
            start, dur, pitch, voice_id = note_tuple
            end = start + dur
            if (start < end_offset and end > start_offset) and (min_pitch <= pitch <= max_pitch):
                pcs_sequence.append(pitch % 12)
                voice_ids_in.add(voice_id)
                voice_pcs.setdefault(voice_id, []).append(pitch)  # raw MIDI

        pcs_tuple, info = self._get_set_info(pcs_sequence)
        # voice_id -> display name mapping
        voice_names = [self.voice_legend.get(vid, {}).get('name', f'V:{vid}') for vid in sorted(voice_ids_in)]
        voice_pcs_detail = {
            vid: [pc for pc in voice_pcs.get(vid, [])]
            for vid in voice_ids_in
        }
        return {
            "pcs": list(pcs_tuple),
            "card": len(pcs_tuple),
            "forte": info['forte'],
            "prime": info['prime'],
            "iv": info['iv'],
            "start_offset": start_offset,
            "end_offset": end_offset,
            "min_pitch": min_pitch,
            "max_pitch": max_pitch,
            "voices": voice_names,
            "voice_pcs_detail": voice_pcs_detail,
        }

    def _on_piano_roll_2d_select(self, eclick, erelease):
        if not self.selection_enabled:
            return

        x1, y1 = eclick.xdata, eclick.ydata
        x2, y2 = erelease.xdata, erelease.ydata

        if x1 is None or x2 is None or y1 is None or y2 is None:
            return

        xmin, xmax = sorted([x1, x2])
        ymin, ymax = sorted([y1, y2])

        window_size = xmax - xmin
        if window_size <= 0.001:
            return

        self.custom_2d_selection = (xmin, xmax, ymin, ymax)

        if window_size > self.max_scale_offset:
            self.max_scale_offset = min(self.total_length, window_size * 1.2)
            self.slider_max_scale.set_val(self.max_scale_offset)
            self._recompute_data_grid()
            self._update_matrix()
            self._redraw_setscape_pcolormesh()

        self.crosshair.set_data([xmin], [window_size])

        self._update_window_overlay()
        self._update_text_info()
        self._capture_background(redraw_dynamic=True)

    def _redraw_setscape_pcolormesh(self):
        self.ax_scape.clear()
        scale_boundaries = np.append(self.scales - self.offset_step / 2, self.scales[-1] + self.offset_step / 2)
        X, Y = np.meshgrid(self.offset_boundaries, scale_boundaries)
        self.quad_mesh = self.ax_scape.pcolormesh(
            X, Y, self.matrix_display,
            cmap=self.custom_cmap,
            norm=self.custom_norm,
            shading='flat'
        )

        self.ax_scape.set_ylabel("Window Size / Scale (Offset)", fontsize=10)
        self.ax_scape.tick_params(axis="both", labelsize=8)
        self.ax_scape.set_xlabel("Actual Offset Position (Quarter Notes)", fontsize=10)
        self.ax_scape.set_ylim(self.scales[0] - self.offset_step / 2, self.scales[-1] + self.offset_step / 2)

        if self.custom_2d_selection:
            cx = self.custom_2d_selection[0]
            cy = self.custom_2d_selection[1] - self.custom_2d_selection[0]
        else:
            cx = self.offset_points[self.selected_offset_idx]
            cy = self.scales[self.selected_scale_idx]

        self.crosshair, = self.ax_scape.plot([cx], [cy], 'r+', markersize=14, markeredgewidth=2)

    def _on_click(self, event):
        # Clickable voice/part checkboxes in the dedicated ax_voices panel
        if event.inaxes == self.ax_voices and event.xdata is not None and event.ydata is not None:
            self._on_voice_checkbox_click(event.xdata, event.ydata)
            return
        # Legacy fallback: also accept clicks inside ax_text if any old rects still live there
        if event.inaxes == self.ax_text and event.xdata is not None and event.ydata is not None:
            if getattr(self, '_voice_check_rects', None) or getattr(self, '_voice_master_rect', None):
                self._on_voice_checkbox_click(event.xdata, event.ydata)
                return

        if event.inaxes == self.ax_scape:
            if self.active_tool in ['Browse', 'Set Select']:
                self._clear_custom_2d_selection()

                self.selected_offset_idx = int(np.searchsorted(self.offset_boundaries, event.xdata, side='right') - 1)
                self.selected_offset_idx = max(0, min(self.selected_offset_idx, self.num_points - 1))
                self.selected_scale_idx = int(np.argmin(np.abs(self.scales - event.ydata)))

                self.crosshair.set_data([event.xdata], [event.ydata])

                if self.active_tool == 'Set Select':
                    self.selection_enabled = True
                    self.rect_selector.set_active(True)
                else:
                    self.selection_enabled = False
                    self.rect_selector.set_active(False)

                self._update_window_overlay()
                self._update_text_info(skip_voice_panel=True)
                self._fast_refresh()
                return

            elif self.active_tool in ['Zoom In (+)', 'Zoom Out (-)']:
                zoom_factor = 0.6 if 'Zoom In' in self.active_tool else 1.6

                cur_xlim = self.ax_scape.get_xlim()
                cur_ylim = self.ax_scape.get_ylim()

                new_width = (cur_xlim[1] - cur_xlim[0]) * zoom_factor
                new_height = (cur_ylim[1] - cur_ylim[0]) * zoom_factor

                full_ymin = self.scales[0] - self.offset_step / 2
                full_ymax = self.scales[-1] + self.offset_step / 2
                max_height = full_ymax - full_ymin

                if new_width > self.total_length:
                    new_width = self.total_length
                if new_height > max_height:
                    new_height = max_height

                center_x, center_y = event.xdata, event.ydata

                new_xmin = center_x - new_width / 2
                new_xmax = center_x + new_width / 2
                new_ymin = center_y - new_height / 2
                new_ymax = center_y + new_height / 2

                if new_xmin < 0:
                    new_xmax += (0 - new_xmin)
                    new_xmin = 0
                if new_xmax > self.total_length:
                    new_xmin -= (new_xmax - self.total_length)
                    new_xmax = self.total_length
                    new_xmin = max(0, new_xmin)

                if new_ymin < full_ymin:
                    new_ymax += (full_ymin - new_ymin)
                    new_ymin = full_ymin
                if new_ymax > full_ymax:
                    new_ymin -= (new_ymax - full_ymax)
                    new_ymax = full_ymax
                    new_ymin = max(full_ymin, new_ymin)

                self.ax_scape.set_xlim(new_xmin, new_xmax)
                self.ax_scape.set_ylim(new_ymin, new_ymax)
                self.ax_piano.set_xlim(new_xmin, new_xmax)

                # Move the scrollbar without triggering a redundant full-canvas
                # redraw (Slider.set_val -> draw_idle).
                self._set_scrollbar_no_draw((new_xmin + new_xmax) / 2)

                # Viewport changed: repaint the two plot axes + dynamic layer.
                # Viewport changed — full redraw required (blit background is stale).
                self._capture_background(redraw_dynamic=True)
                return

        # Focus tracking for Pan View keyboard stepping + handle turns red
        if event.inaxes == self.ax_scrollbar:
            if not self._pan_step_active:
                self._pan_step_active = True
                self.scrollbar._handle.set_markerfacecolor('#DD2222')
                self.scrollbar._handle.set_markeredgecolor('#DD2222')
                self._bg = None
                self.fig.canvas.draw_idle()
                return
        else:
            if self._pan_step_active:
                self._pan_step_active = False
                self.scrollbar._handle.set_markerfacecolor('white')
                self.scrollbar._handle.set_markeredgecolor('.75')
                self._bg = None
                self.fig.canvas.draw_idle()
                return
    def _reload_and_refresh(self, target_path, is_local=False):
        print(f"Loading target: {target_path} (is_local={is_local})")
        self._load_score_data(target_path, is_local=is_local)
        self._parse_score()
        self._recompute_data_grid()

        self.slider_max_scale.valmax = self.total_length
        self.slider_max_scale.set_val(self.max_scale_offset)
        self.slider_step.set_val(self.offset_step)

        self.scrollbar.valmax = self.total_length
        self.scrollbar.eventson = False
        self.scrollbar.set_val(self.total_length / 2.0)
        self.scrollbar.eventson = True

        self._update_matrix()
        self._redraw_setscape_pcolormesh()

        self._on_reset_view(None)
        self._draw_base_piano_roll()

        self.rect_selector = _EdgeOnlyRectangleSelector(
            self.ax_piano,
            self._on_piano_roll_2d_select,
            useblit=True,
            props=dict(alpha=0.3, facecolor='red', edgecolor='red', linewidth=1.5),
            interactive=True,
            drag_from_anywhere=False,
            spancoords='data'
        )
        self.radio_tools.set_active(0)
        self.selection_enabled = False
        self.rect_selector.set_active(False)

        self._update_window_overlay()
        self._update_text_info()

        # 更新格式化文本
        base_name = os.path.basename(self.xml_path)
        corpus_display_text = format_corpus_two_lines(base_name)
        self.textbox_corpus.eventson = False
        self.textbox_corpus.set_val(corpus_display_text)
        self.textbox_corpus.eventson = True

        self._capture_background(redraw_dynamic=True)

    def _on_corpus_submit(self, text):
        lines = [line.strip() for line in text.split('\n') if line.strip()]
        clean_lines = [l for l in lines if l.lower() not in ['corpus', 'corpus:']]
        corpus_path = "".join(clean_lines).strip('"').strip("'")

        if not corpus_path:
            return

        if os.path.exists(corpus_path):
            self._reload_and_refresh(corpus_path, is_local=True)
            return

        try:
            self._reload_and_refresh(corpus_path, is_local=False)
        except Exception:
            messagebox.showwarning("Corpus Error", "Could not find corpus piece. Opening local file dialog.")
            self._on_select_file(None)

    def _on_select_file(self, event):
        file_path = filedialog.askopenfilename(
            title="Choose Local Music Score File",
            filetypes=[
                ("Supported Score Files", "*.xml *.mxl *.musicxml *.mscz *.mid *.midi"),
                ("MuseScore Files", "*.mscz"),
                ("MusicXML Files", "*.xml *.mxl *.musicxml"),
                ("MIDI Files", "*.mid *.midi"),
                ("All Files", "*.*")
            ]
        )
        if file_path:
            try:
                self._reload_and_refresh(file_path, is_local=True)
            except Exception as e:
                messagebox.showerror("File Error", f"Failed to parse local file: {e}")

    def _draw_base_piano_roll(self):
        """Render base Piano Roll with full-height voice-colored bars.

        When several voices hit the same pitch at the same time they are drawn
        as one vertical color strip (top-to-bottom by voice id), so overlapping
        parts stay clearly distinguishable instead of covering each other.
        """
        if not hasattr(self, 'ax_piano'):
            return
        self.ax_piano.clear()
        for pitch in range(self.min_midi, self.max_midi + 1):
            if pitch % 12 in [1, 3, 6, 8, 10]:
                self.ax_piano.axhspan(pitch - 0.5, pitch + 0.5, color='#f0f0f0', zorder=1)

        notes_to_draw = self.piano_roll_notes
        if hasattr(self, 'active_voice_ids'):
            notes_to_draw = [
                nt for nt in self.piano_roll_notes
                if nt[3] in self.active_voice_ids
            ]

        def _color(voice_id):
            return self.voice_legend.get(voice_id, {}).get('color', '#333333')

        # 合并模式：所有声部直接画在同一 pitch 全高位置，重叠时靠半透明叠加混合
        # 每个声部固定 alpha=0.4，4个声部全叠时 ≈ 1 - (1-0.4)^4 = 0.87 不透明
        # 性能：把几千个音符矩形合并成两个 PatchCollection 批量渲染，
        # 避免逐个 add_patch 导致每次全图 redraw 都要重绘数千个独立 artist。
        OVERLAY_ALPHA = 0.40
        fill_rects = []
        edge_rects = []
        for start, dur, pitch, voice_id in notes_to_draw:
            face_color = _color(voice_id)
            fill_rects.append(patches.Rectangle(
                (start, pitch - 0.5), dur, 1.0,
                linewidth=0.0,
                facecolor=face_color, alpha=OVERLAY_ALPHA
            ))
            edge_rects.append(patches.Rectangle(
                (start, pitch - 0.5), dur, 1.0,
                linewidth=0.6, edgecolor=face_color, facecolor='none',
                alpha=0.7
            ))
        if fill_rects:
            fill_col = PatchCollection(fill_rects, match_original=True, zorder=2)
            self.ax_piano.add_collection(fill_col)
        if edge_rects:
            edge_col = PatchCollection(edge_rects, match_original=True, zorder=3)
            self.ax_piano.add_collection(edge_col)

        self.ax_piano.set_xlim(0, self.total_length)
        self.ax_piano.set_ylim(self.min_midi - 1, self.max_midi + 1)
        self.ax_piano.set_ylabel("MIDI Pitch", fontsize=10)
        self.ax_piano.set_xlabel("Offset Position", fontsize=10)
        self.ax_piano.tick_params(axis="both", labelsize=8)

        # MIDI 刻度：每 5 半音标 "MIDI 音名"，不画更细的 minor tick
        from matplotlib.ticker import MultipleLocator, FixedLocator, FixedFormatter
        note_names = ['C', 'C#', 'D', 'D#', 'E', 'F', 'F#', 'G', 'G#', 'A', 'A#', 'B']
        ymin_int = int(np.floor(self.min_midi / 5.0)) * 5
        ymax_int = int(np.ceil(self.max_midi / 5.0)) * 5
        all_midis = list(range(ymin_int, ymax_int + 1, 5))
        all_labels = [f"{m} {note_names[m % 12]}{m // 12 - 1}" for m in all_midis]
        self.ax_piano.yaxis.set_major_locator(FixedLocator(all_midis))
        self.ax_piano.yaxis.set_major_formatter(FixedFormatter(all_labels))
        self.ax_piano.yaxis.set_minor_locator(MultipleLocator(1))
        self.ax_piano.tick_params(axis='y', which='major', labelsize=7, length=4)
        # 不画 minor tick / 网格
        self.ax_piano.tick_params(axis='y', which='minor', length=0, color='none')
        self.ax_piano.grid(axis='y', which='major', linestyle=':', linewidth=0.4, color='#bbbbbb', alpha=0.7, zorder=0)
        self.ax_piano.grid(axis='y', which='minor', visible=False)

        self.window_patch = None

    def _update_window_overlay(self):
        if self.custom_2d_selection:
            start_o, end_o, ymin, ymax = self.custom_2d_selection
            width = end_o - start_o
            height = ymax - ymin
            title_str = f"Piano Roll View | Active Window: {start_o:.2f} to {end_o:.2f} (MIDI: {ymin:.1f}-{ymax:.1f})"
        else:
            info = self.data_grid[(self.selected_scale_idx, self.selected_offset_idx)]
            start_o, end_o = info["start_offset"], info["end_offset"]
            width = end_o - start_o
            height = (self.max_midi - self.min_midi + 2)
            ymin = self.min_midi - 1
            title_str = f"Piano Roll View | Active Window: {start_o:.2f} to {end_o:.2f} (Full Pitch)"

        # Reuse one cached rectangle (dynamic blit layer) instead of rebuild
        wp = getattr(self, 'window_patch', None)
        if wp is None or wp not in self.ax_piano.patches:
            wp = patches.Rectangle(
                (start_o, ymin), width, height,
                linewidth=2.0, edgecolor='red', facecolor='none',
                linestyle='--', zorder=4
            )
            self.window_patch = self.ax_piano.add_patch(wp)
            self.window_patch.set_animated(True)
            self._add_blit_artist(self.window_patch)
        else:
            self.window_patch.set_xy((start_o, ymin))
            self.window_patch.set_width(width)
            self.window_patch.set_height(height)
        self.ax_piano.set_title(title_str, fontsize=8, loc='left')

    def _on_slider_release(self, val):
        self.max_scale_offset = self.slider_max_scale.val
        self.slider_step.set_val(self.slider_step.val)

    def _on_refresh(self, event):
        """点击 Refresh 按钮后，根据当前的滑块数值重新计算网格并刷新图表"""
        print("Refreshing visualization and recalculating data grid...")
        self.max_scale_offset = self.slider_max_scale.val
        self.offset_step = self.slider_step.val

        # Honor voice/part selection before grid recomputation.
        # _refresh_filtered_data() already recomputes grid/matrix/overlay/text.
        self._refresh_filtered_data()

        self.selected_offset_idx = min(self.selected_offset_idx, self.num_points - 1)
        self.selected_scale_idx = min(self.selected_scale_idx, self.num_scales - 1)

        self._capture_background(redraw_dynamic=True)

    def _on_reset_view(self, event):
        default_ymin = self.scales[0] - self.offset_step / 2
        default_ymax = self.scales[-1] + self.offset_step / 2

        self.ax_scape.set_xlim(0, self.total_length)
        self.ax_scape.set_ylim(default_ymin, default_ymax)
        self.ax_piano.set_xlim(0, self.total_length)

        self.scrollbar.eventson = False
        self.scrollbar.set_val(self.total_length / 2.0)
        self.scrollbar.eventson = True

        self._clear_custom_2d_selection()
        self.radio_tools.set_active(0)
        self.selection_enabled = False
        if hasattr(self, 'rect_selector'):
            self.rect_selector.set_active(False)

        self._capture_background(redraw_dynamic=True)

    def _on_scroll_pan(self, val):
        cur_xlim = self.ax_scape.get_xlim()
        visible_width = cur_xlim[1] - cur_xlim[0]

        new_center = self.scrollbar.val
        new_xmin = new_center - visible_width / 2
        new_xmax = new_center + visible_width / 2

        if new_xmin < 0:
            new_xmax -= new_xmin
            new_xmin = 0
        if new_xmax > self.total_length:
            new_xmin -= (new_xmax - self.total_length)
            new_xmax = self.total_length
            new_xmin = max(0, new_xmin)

        self.ax_scape.set_xlim(new_xmin, new_xmax)
        self.ax_piano.set_xlim(new_xmin, new_xmax)
        # Viewport changed — full redraw required (blit background is stale).
        self._capture_background(redraw_dynamic=True)

    def _on_card_toggle(self, label):
        if label == "All":
            # Master checkbox: checked -> all; unchecked -> none
            if self.check_box.get_status()[0]:
                self.cardinality_mask = set(range(1, 13))
            else:
                self.cardinality_mask = set()
            self._refresh_card_check_visual(keep_master=True)
        else:
            card = int(label)
            if card in self.cardinality_mask:
                self.cardinality_mask.remove(card)
            else:
                self.cardinality_mask.add(card)
            self._sync_master_card()

        self._update_matrix()
        self.quad_mesh.set_array(self.matrix_display.ravel())
        self._capture_background(redraw_dynamic=True)

    def _sync_master_card(self):
        """Set the master All checkbox active only if all 1-12 are active."""
        all_on = self.cardinality_mask == set(range(1, 13))
        self.check_box.eventson = False
        try:
            self.check_box.set_active(0, all_on)
        finally:
            self.check_box.eventson = True

    def _refresh_card_check_visual(self, keep_master=False):
        """Synchronize all cardinality checkboxes with self.cardinality_mask.

        Index 0 is the master All box; indices 1..12 are cardinalities 1..12.
        """
        all_on = self.cardinality_mask == set(range(1, 13))
        self.check_box.eventson = False
        try:
            if keep_master:
                # master state is already what the user clicked
                all_on = self.check_box.get_status()[0]
            for i in range(1, 13):
                self.check_box.set_active(i, i in self.cardinality_mask)
            self.check_box.set_active(0, all_on)
        finally:
            self.check_box.eventson = True

    def _on_voice_checkbox_click(self, x, y):
        """Toggle a voice selection visually. Call Refresh (or _refresh_filtered_data) to recompute."""

        def _hit(rect):
            if not rect:
                return False
            rx, ry, rw, rh = rect
            return rx <= x <= rx + rw and ry <= y <= ry + rh

        # Master "All Voices" checkbox: checked -> all, unchecked -> none
        if _hit(getattr(self, '_voice_master_rect', None)):
            all_ids = set(self.voice_legend.keys())
            if self.active_voice_ids == all_ids:
                self.active_voice_ids = set()
            else:
                self.active_voice_ids = set(all_ids)
            self._update_text_info()
            self._capture_background(redraw_dynamic=True)
            return

        rects = getattr(self, '_voice_check_rects', {})
        for v_id, (rx, ry, rw, rh) in rects.items():
            if rx <= x <= rx + rw and ry <= y <= ry + rh:
                if v_id in self.active_voice_ids:
                    self.active_voice_ids.remove(v_id)
                else:
                    self.active_voice_ids.add(v_id)
                # Visual-only toggle; click Refresh to recompute with new voice selection
                self._update_text_info()
                self._capture_background(redraw_dynamic=True)
                return

    def _refresh_filtered_data(self):
        """Filter notes/pcs arrays by active voices, then recompute piano roll + grid."""
        # Rebuild the working piano-roll list from the full data so the
        # draw routine already sees only selected voices.
        self.piano_roll_notes = [
            nt for nt in self.full_piano_roll_notes
            if nt[3] in self.active_voice_ids
        ]
        self._draw_base_piano_roll()

        # Rebuild filtered event arrays from full data
        filt_starts, filt_ends, filt_pcs = [], [], []
        for ev_idx, v_id in enumerate(self.event_voice_ids):
            if v_id in self.active_voice_ids:
                filt_starts.append(self.full_starts_arr[ev_idx])
                filt_ends.append(self.full_ends_arr[ev_idx])
                filt_pcs.append(self.full_pcs_arr[ev_idx])
        self.starts_arr = np.array(filt_starts)
        self.ends_arr = np.array(filt_ends)
        self.pcs_arr = filt_pcs

        self._recompute_data_grid()
        self._update_matrix()
        self._redraw_setscape_pcolormesh()
        self._update_window_overlay()
        self._update_text_info()

    def _format_voices_block(self, voices_in, max_chars=60, voice_pcs_detail=None, voice_legend=None):
        """Format voice names into a multi-line block for the text panel.
        When voice_pcs_detail is provided, appends each voice's PCs in brackets.
        Returns a string starting with "\n" so it appends to the existing text_str."""
        import re
        if not voices_in:
            return "\nVoices: (none)"

        def _short(name):
            return re.sub(r"\s*\(V:\d+\)\s*$", "", name).strip() or name

        short_names = [_short(v) for v in voices_in]
        prefix = f"Voices ({len(short_names)}): "
        single = prefix + ", ".join(short_names)
        # If we have per-voice PC detail, show it below the summary
        if voice_pcs_detail and voice_legend:
            detail_lines = []
            name_to_id = {}
            for v_id, v_info in voice_legend.items():
                name_to_id[_short(v_info['name'])] = v_id
            # 用满可用宽度，只留最小边距
            ax_bbox = self.ax_text.get_position().bounds
            fig_w = self.fig.get_figwidth()
            ax_w_in = ax_bbox[2] * fig_w
            mono_cpw = 4.8  # monospace 8pt 每字符≈4.8pt
            margin_chars = 14  # 缩进 + 声部名 + "[" 的最小值
            usable_chars = int((ax_w_in * 72 - margin_chars * mono_cpw) / mono_cpw)
            wrap_chunk = max(4, usable_chars // 3)  # 每个 PC = "XX " ≈ 3 字符
            # 估算总行数，如果超出框高则截断
            # ax_text 高度 ≈ 0.40 fig-fraction × 12in = 4.8in, 每行 ≈ 9.2pt (8pt × 1.15 linespacing)


            def _midi_to_display(midi):
                """Convert MIDI pitch like 69 to 'A5' then '9(A5)'."""
                try:
                    p = m21.pitch.Pitch(midi=int(midi))
                    name = p.nameWithOctave
                    return f"{p.pitchClass}({name})"
                except Exception:
                    return str(midi)

            def _write_voice_details_per_part(nm_list, pcs_detail):
                lines = []
                # 每个声部最多占 2 行，超出的部分用 "..." 截断该声部，不影响后续声部
                for nm in nm_list:
                    v_id = name_to_id.get(nm)
                    raw = pcs_detail.get(v_id, [])
                    if not raw:
                        lines.append(f"    {nm}: []")
                        continue
                    display_items = [_midi_to_display(m) for m in raw]
                    parts = [" ".join(display_items[i:i+wrap_chunk]) for i in range(0, len(display_items), wrap_chunk)]
                    voice_rows = []
                    for i_part, part in enumerate(parts):
                        if i_part == 0 and len(parts) == 1:
                            voice_rows.append(f"    {nm}: [{part}]")
                        elif i_part == 0:
                            voice_rows.append(f"    {nm}: [{part}")
                        elif i_part == len(parts) - 1:
                            voice_rows.append(f"           {part}]")
                        else:
                            voice_rows.append(f"           {part}")
                    # 最多 2 行，多余行换成省略号
                    if len(voice_rows) > 2:
                        voice_rows = voice_rows[:2]
                        last = voice_rows[-1].rstrip()
                        if last.endswith(']'):
                            voice_rows[-1] = last[:-1].rstrip() + " ...]"
                        else:
                            voice_rows[-1] = last + " ...]"
                    lines.extend(voice_rows)
                return lines

            detail_lines = _write_voice_details_per_part(short_names, voice_pcs_detail)
            return "\n" + single + "\n" + "\n".join(detail_lines)
        # fallback: single line or wrap
        if len(single) <= max_chars:
            return "\n" + single
        line_width = max_chars
        rows = []
        current = prefix.rstrip()
        cur_len = len(current)
        for i, nm in enumerate(short_names):
            piece = nm + (", " if i < len(short_names) - 1 else "")
            if cur_len + len(piece) <= line_width:
                current += piece
                cur_len += len(piece)
            else:
                rows.append(current.rstrip(", "))
                current = "         " + nm + (", " if i < len(short_names) - 1 else "")
                cur_len = len(current)
        if current.strip():
            rows.append(current.rstrip(", "))
        return "\n" + "\n".join(rows)

    def _annotated_pcs_line(self, pcs_list, voice_pcs_detail, global_deduped_pcs=None):
        """Build PCs lines.
        When global_deduped_pcs is provided (pre-computed time-ordered dedup list),
        use it directly.  Otherwise fall back to a flat prime-form list.
        Returns a list of strings (one per line) for the text display.
        """
        import re

        def _short(name):
            return re.sub(r"\s*\(V:\d+\)\s*$", "", name).strip() or name

        def _midi_to_display(midi):
            try:
                p = m21.pitch.Pitch(midi=int(midi))
                return f"{p.pitchClass}({p.nameWithOctave})"
            except Exception:
                return str(midi)

        # Pre-computed global-dedup path (preferred)
        if global_deduped_pcs is not None:
            lines = ["PCs (time-ordered, dedup):"]
            display_items = []
            for item in global_deduped_pcs:
                pc, midi = item if isinstance(item, tuple) else (item, None)
                if midi is not None:
                    try:
                        p_obj = m21.pitch.Pitch(midi=int(midi))
                        display_items.append(f"{pc}({p_obj.nameWithOctave})")
                    except Exception:
                        display_items.append(str(pc))
                else:
                    display_items.append(str(pc))
            per_line = 12
            chunks = [" ".join(display_items[i:i+per_line])
                      for i in range(0, len(display_items), per_line)]
            for chunk in chunks:
                lines.append(f"  {chunk}")
            return lines

        # Voice-grouped fallback (kept for safety)
        if voice_pcs_detail:
            lines = ["PCs (global time order, dedup):"]
            events = []
            voice_pitches_with_offset = {}
            for nt in getattr(self, 'piano_roll_notes', []):
                start, dur, pitch, voice_id = nt
                if voice_id in voice_pcs_detail:
                    pc = pitch % 12
                    voice_pitches_with_offset.setdefault(voice_id, []).append((start, pc))
            for v_id, pairs in voice_pitches_with_offset.items():
                for offset, pc in pairs:
                    events.append((offset, v_id, pc))
            events.sort(key=lambda x: (x[0], x[1]))
            seen = set()
            deduped_pcs = []
            for _, _, pc in events:
                if pc not in seen:
                    seen.add(pc)
                    deduped_pcs.append(pc)
            if not deduped_pcs:
                return ["PCs: (none)"]
            display_items = [str(pc) for pc in deduped_pcs]
            per_line = 12
            chunks = [" ".join(display_items[i:i+per_line])
                      for i in range(0, len(display_items), per_line)]
            for chunk in chunks:
                lines.append(f"  {chunk}")
            return lines

        # Fallback: flat prime-form list
        if not pcs_list:
            return ["PCs: (none)"]
        items = []
        for pc in pcs_list:
            try:
                p = m21.pitch.Pitch(midi=int(pc))
                items.append(f"{pc}({p.nameWithOctave})")
            except Exception:
                items.append(str(pc))
        per_line = 10
        lines = []
        for i in range(0, len(items), per_line):
            chunk = items[i:i+per_line]
            if i == 0:
                lines.append("PCs: " + " ".join(chunk))
            else:
                lines.append("      " + " ".join(chunk))
        return lines

    def _update_text_info(self, skip_voice_panel=False):
        """Update analysis text in ax_text (text-only). Voice checkboxes are drawn separately in ax_voices via _draw_voice_panel.

        Performance: the body text reuses one cached Text artist (set_text)
        instead of clear()+rebuild, so a Browse click only re-renders a single
        text object instead of recreating the whole text axes.
        """
        # 完全关闭 ax_text 的坐标轴显示（隐藏 spines + ticks + tick labels + axis labels）
        # 不影响 transAxes 文本定位，set_xlim/set_ylim 也不再需要
        self.ax_text.axis('off')
        self.ax_text.set_facecolor('none')

        if self.custom_2d_selection:
            x1, x2, y1, y2 = self.custom_2d_selection
            info = self._analyze_custom_2d_range(x1, x2, y1, y2)
            window_sz = x2 - x1
            pitch_str = f"\nPitch: {y1:.1f}-{y2:.1f}"
            # 选中态下额外统计涉及声部（实时从分析结果读取）—— 完整显示，不截断
            voices_in = info.get('voices', [],) if info else []
            voice_pcs_detail = info.get('voice_pcs_detail', {}) if info else {}
            voice_block = self._format_voices_block(voices_in, voice_pcs_detail=voice_pcs_detail, voice_legend=self.voice_legend)
            _gvd = voice_pcs_detail
        else:
            info = self.data_grid.get((self.selected_scale_idx, self.selected_offset_idx), None)
            window_sz = self.scales[self.selected_scale_idx] if info else 0.0
            pitch_str = ""
            # data_grid 路径：实时从 piano_roll_notes 统计活跃声部（完整显示）
            if info is not None:
                # Ensure Forte/prime/iv computed before reading
                if "forte" not in info:
                    pcs_key = tuple(sorted(info.get("pcs", [])))
                    if pcs_key in self._forte_cache:
                        forte, prime, iv = self._forte_cache[pcs_key]
                    else:
                        forte, prime, iv = fast_pitch_class_info(list(pcs_key))
                        self._forte_cache[pcs_key] = (forte, prime, iv)
                    info["forte"] = forte
                    info["prime"] = prime
                    info["iv"] = iv
                grid_voice_pcs = {}
                for nt in getattr(self, 'piano_roll_notes', []):
                    start, dur, pitch, voice_id = nt
                    if start < info['end_offset'] and start + dur > info['start_offset']:
                        grid_voice_pcs.setdefault(voice_id, []).append(pitch)  # raw MIDI
                active_vids = sorted(grid_voice_pcs.keys())
                voices_in = [
                    self.voice_legend.get(vid, {}).get('name', f'V:{vid}')
                    for vid in active_vids
                ]
                voice_block = self._format_voices_block(voices_in, voice_pcs_detail=grid_voice_pcs, voice_legend=self.voice_legend)
                _gvd = grid_voice_pcs
            else:
                voice_block = ""
                _gvd = {}

        # ── Pre-compute time-ordered deduped PCs for annotated PCS line ──
        global_deduped = None
        if info:
            events = []
            for nt in getattr(self, 'piano_roll_notes', []):
                start, dur, pitch, voice_id = nt
                if start < info['end_offset'] and start + dur > info['start_offset']:
                    if self.custom_2d_selection:
                        x1, x2, y1, y2 = self.custom_2d_selection
                        if not (y1 <= pitch <= y2):
                            continue
                    pc = pitch % 12
                    events.append((start, voice_id, pc, pitch))  # keep raw MIDI for note name
            events.sort(key=lambda x: (x[0], x[1]))
            seen = set()
            global_deduped = []
            for _, _, pc, midi in events:
                if pc not in seen:
                    seen.add(pc)
                    global_deduped.append((pc, midi))

        if info:
            pcs_lines = self._annotated_pcs_line(info['pcs'], _gvd, global_deduped_pcs=global_deduped)
            pcs_annotated = "\n".join(pcs_lines)
            text_str = (
                f"Mode: [{self.active_tool}]  Offset: {info['start_offset']:.1f}-{info['end_offset']:.1f}{pitch_str}\n"
                f"Window: {window_sz:.1f}  Step: {self.offset_step:.1f}\n"
                f"Forte: {info['forte']}  Card: {info['card']}\n"
                f"Prime: {info['prime']}\n"
                f"{pcs_annotated}\n"
                f"IV: {info['iv']}{voice_block}"
            )
        else:
            text_str = "No Data Selected"
        if getattr(self, '_text_artist', None) is None:
            self._text_artist = self.ax_text.text(
                0.002, 0.97, text_str,
                transform=self.ax_text.transAxes,
                fontsize=7.5,
                verticalalignment='top',
                fontfamily='monospace',
                # 文本本身已按行组织（含 \n），wrap=True 会在每次重绘时
                # 对长文本重新布局（~45ms），关掉后仅 ~7ms，视觉一致。
                wrap=False,
                linespacing=1.10
            )
            self._text_artist.set_animated(True)
            self._add_blit_artist(self._text_artist)
        else:
            self._text_artist.set_text(text_str)
        # ax_text 已 axis('off')，无需再设置 xlim/ylim（保留会触发自动 tick 标签）

        # 声部勾选面板移到独立子图 ax_voices
        if not skip_voice_panel:
            self._draw_voice_panel()

    def _draw_voice_panel(self):
        """Render the clickable Voices / Parts checkboxes inside ax_voices
        with a background card and border."""
        self.ax_voices.clear()
        self.ax_voices.set_facecolor('none')
        self.ax_voices.set_xlim(0, 1)
        self.ax_voices.set_ylim(0, 1)
        self.ax_voices.axis('off')

        artists = []

        # Background card: rounded rectangle with subtle border
        artists.append(patches.FancyBboxPatch(
            (0.01, 0.01), 0.98, 0.98,
            boxstyle="round,pad=0.015",
            transform=self.ax_voices.transAxes,
            facecolor='#FAFBFC', edgecolor='#B0B8C1',
            linewidth=1.2, zorder=0, clip_on=False
        ))

        # 标题
        self.ax_voices.set_title(
            'Voices / Parts',
            fontsize=6.5,
            fontweight='bold',
            loc='center',
            pad=4,
            color='#333333'
        )

        # Shift all content to the right within the card
        shift_x = 0.12  # rightward offset

        # "All Voices" master checkbox
        all_voice_on = (
            len(self.voice_legend) > 0
            and getattr(self, 'active_voice_ids', set()) == set(self.voice_legend.keys())
        )
        y = 0.83
        cb_w, cb_h = 0.05, 0.10
        cb_x = 0.06 + shift_x
        self._voice_master_rect = (cb_x, y - cb_h / 2, cb_w, cb_h)
        mark = "✓" if all_voice_on else " "
        artists.append(self.ax_voices.text(
            cb_x + cb_w / 2, y,
            mark,
            transform=self.ax_voices.transAxes,
            fontsize=7,
            fontweight='bold',
            color='#1E7E34',
            verticalalignment='center',
            horizontalalignment='center',
            fontfamily='DejaVu Sans',
            zorder=4
        ))
        artists.append(self.ax_voices.add_patch(
            patches.Rectangle(
                (cb_x, y - cb_h / 2), cb_w, cb_h,
                transform=self.ax_voices.transAxes,
                facecolor='#FFFFFF',
                edgecolor='#444444',
                linewidth=1.5,
                joinstyle='miter',
                zorder=3
            )
        ))
        artists.append(self.ax_voices.text(
            cb_x + cb_w + 0.10, y, "All Voices",
            transform=self.ax_voices.transAxes,
            fontsize=5.5,
            color='#333333',
            fontweight='bold',
            verticalalignment='center',
            fontfamily='monospace'
        ))

        # individual voice checkboxes
        self._voice_check_rects = {}
        if not self.voice_legend:
            artists.append(self.ax_voices.text(
                0.5, 0.45, "No Voice Info",
                transform=self.ax_voices.transAxes,
                fontsize=8,
                verticalalignment='center',
                horizontalalignment='center',
                fontfamily='monospace',
                color='#666666'
            ))
            self._replace_voice_artists(artists)
            return

        y_start = 0.60
        y_step = 0.14
        for idx, (v_id, v_info) in enumerate(self.voice_legend.items()):
            display_name = v_info['name']
            if len(display_name) > 22:
                display_name = display_name[:20] + ".."

            y_i = y_start - idx * y_step
            cb_x_i = 0.06 + shift_x
            cb_y_i = y_i - cb_h / 2
            self._voice_check_rects[v_id] = (cb_x_i, cb_y_i, cb_w, cb_h)

            checked = v_id in getattr(self, 'active_voice_ids', set())
            mark = "✓" if checked else " "
            artists.append(self.ax_voices.text(
                cb_x_i + cb_w / 2, y_i,
                mark,
                transform=self.ax_voices.transAxes,
                fontsize=7,
                fontweight='bold',
                color='#1E7E34',
                verticalalignment='center',
                horizontalalignment='center',
                fontfamily='DejaVu Sans',
                zorder=4
            ))
            artists.append(self.ax_voices.add_patch(
                patches.Rectangle(
                    (cb_x_i, cb_y_i), cb_w, cb_h,
                    transform=self.ax_voices.transAxes,
                    facecolor='#FFFFFF',
                    edgecolor='#444444',
                    linewidth=1.5,
                    joinstyle='miter',
                    zorder=3
                )
            ))
            # 颜色色块
            artists.append(self.ax_voices.add_patch(
                patches.Rectangle(
                    (cb_x_i + cb_w + 0.02, y_i - cb_h / 2 + 0.01),
                    0.05, cb_h - 0.02,
                    transform=self.ax_voices.transAxes,
                    facecolor=v_info['color'], edgecolor=v_info['color'],
                    linewidth=0.8, zorder=2
                )
            ))
            # 声部名称
            artists.append(self.ax_voices.text(
                cb_x_i + cb_w + 0.10, y_i, display_name,
                transform=self.ax_voices.transAxes,
                fontsize=6,
                color=v_info['color'],
                fontweight='bold',
                verticalalignment='center',
                fontfamily='monospace'
            ))

        self._replace_voice_artists(artists)



def launch(score_path=None, score=None):
    """Launch the InteractiveDynamicSetExplorer.

    score_path: optional local score file to load directly.
    score: optional already-parsed music21 score (bypasses file parsing).
    """
    explorer = InteractiveDynamicSetExplorer(score_path=score_path, score=score)
    return explorer


if __name__ == "__main__":
    # Support --path <file> so the PyQt main app can launch it as a subprocess
    _target = None
    if len(_sys.argv) > 1:
        _target = _sys.argv[1]
        if _target.startswith("--path="):
            _target = _target[len("--path="):]
    explorer = InteractiveDynamicSetExplorer(score_path=_target)
