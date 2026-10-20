import os
import tempfile
import zipfile
import hashlib
import colorsys
# 强制指定使用 Tkinter 交互后端，确保能够弹出交互式窗口
import matplotlib

matplotlib.use('TkAgg')

import tkinter as tk
from tkinter import filedialog, messagebox, simpledialog
import matplotlib.pyplot as plt
from matplotlib.widgets import CheckButtons, Slider, RadioButtons, Button, TextBox, RectangleSelector
from matplotlib.colors import ListedColormap, BoundaryNorm
import numpy as np
import matplotlib.patches as patches

# Configure Matplotlib global font and Unicode settings (采用学术推荐的无衬线体)
plt.rcParams['font.sans-serif'] = ['Arial', 'DejaVu Sans', 'Helvetica']
plt.rcParams['axes.unicode_minus'] = False

# Configure temporary cache directory for music21
temp_dir = os.path.join(tempfile.gettempdir(), "music21")
os.makedirs(temp_dir, exist_ok=True)

import music21 as m21

env = m21.environment.UserSettings()
env["directoryScratch"] = temp_dir


def generate_high_contrast_palette(num_colors=256):
    """
    Generate a high-contrast palette using golden ratio hue distribution.
    Ensures adjacent indices have maximum visual contrast.
    """
    colors = [[1.0, 1.0, 1.0, 1.0]]  # Index 0 is reserved for background (white)
    golden_ratio_conjugate = 0.618033988749895
    h = 0.1  # Starting hue

    for i in range(1, num_colors):
        h = (h + golden_ratio_conjugate) % 1.0
        s = 0.85 if (i % 2 == 0) else 0.65
        l = 0.45 if (i % 3 == 0) else (0.60 if i % 3 == 1 else 0.35)

        r, g, b = colorsys.hls_to_rgb(h, l, s)
        colors.append([r, g, b, 1.0])

    return np.array(colors)


def fast_pitch_class_info(pcs):
    """Fast pitch-class set analysis using pure Python and music21."""
    if not pcs:
        return "Empty", "[]", "[0 0 0 0 0 0]"
    c = m21.chord.Chord(pcs)
    forte = c.forteClass if c.forteClass else "N/A"
    prime = str(c.primeForm)
    iv = str(c.intervalVector)
    return forte, prime, iv


def format_corpus_two_lines(text):

    if not text:
        return "Corpus:\n"

    max_len_line = 45
    if len(text) <= max_len_line:
        file_part = text
    else:
        mid = min(len(text), max_len_line)
        best_split = mid
        for i in range(mid - 3, min(len(text), mid + 5)):
            if 0 <= i < len(text) and text[i] in ['_', ' ', '-']:
                best_split = i + 1
                break
        file_part = f"{text[:best_split].strip()}\n{text[best_split:].strip()}"

    return f"Corpus:\n\n{file_part}"


class InteractiveDynamicSetExplorer:
    def __init__(self):
        # Initialize hidden Tkinter root window for dialog boxes
        self.root = tk.Tk()
        self.root.withdraw()
        self.root.attributes('-topmost', True)

        # Generate pre-calculated high-contrast palette
        self.palette = generate_high_contrast_palette(num_colors=512)

        # Predefined voice colors
        self.voice_colors = ['#2E75B6', '#C65911', '#548235', '#BF8F00', '#203764', '#595959', '#A61C1C']
        self.voice_legend = {}

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
        self.piano_roll_notes = []  # List of tuples: (start, dur, pitch, voice_id)
        self.voice_legend = {}

        if hasattr(self.score, 'hasPartLikeTree') and self.score.hasPartLikeTree():
            parts = self.score.parts
        elif hasattr(self.score, 'parts') and len(self.score.parts) > 0:
            parts = self.score.parts
        else:
            parts = [self.score]

        for part_idx, part in enumerate(parts):
            part_name = getattr(part, 'partName', None)
            if not part_name:
                part_name = f"Part {part_idx + 1}"

            for el in part.recurse().getElementsByClass(["Note", "Chord"]):
                abs_start = float(el.getOffsetInHierarchy(self.score))
                dur = float(el.quarterLength)
                abs_end = abs_start + dur

                voice_id = part_idx
                voice_obj = el.getContextByClass('Voice')
                if voice_obj and hasattr(voice_obj, 'id') and voice_obj.id is not None:
                    try:
                        voice_id = int(str(voice_obj.id)) + part_idx * 10
                    except ValueError:
                        pass

                if voice_id not in self.voice_legend:
                    color_hex = self.voice_colors[voice_id % len(self.voice_colors)]
                    self.voice_legend[voice_id] = {
                        "name": f"{part_name} (V:{voice_id})",
                        "color": color_hex
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

        self.starts_arr = np.array(starts_list)
        self.ends_arr = np.array(ends_list)
        self.pcs_arr = pcs_list

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
        self.pcs_cache = {}

        self.custom_2d_selection = None
        self.active_tool = 'Browse'
        self.selection_enabled = False

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
        if not forte_name or forte_name in ["Empty", "N/A"]:
            return 0
        hash_val = int(hashlib.md5(forte_name.encode('utf-8')).hexdigest(), 16)
        index = (hash_val % (len(self.palette) - 1)) + 1
        return index

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

        self.data_grid = {}
        for s_idx, scale_offset in enumerate(self.scales):
            for o_idx in range(self.num_points):
                start_offset = self.offset_boundaries[o_idx]
                end_offset = start_offset + scale_offset

                mask = (self.starts_arr < end_offset) & (self.ends_arr > start_offset)
                pcs_sequence = []
                for idx in np.where(mask)[0]:
                    pcs_sequence.extend(self.pcs_arr[idx])
                pcs_tuple, info = self._get_set_info(pcs_sequence)

                self.data_grid[(s_idx, o_idx)] = {
                    "pcs": list(pcs_tuple),
                    "card": len(pcs_tuple),
                    "forte": info['forte'],
                    "prime": info['prime'],
                    "iv": info['iv'],
                    "start_offset": start_offset,
                    "end_offset": min(self.total_length, end_offset)
                }

    def _update_matrix(self):
        self.matrix_display = np.zeros((self.num_scales, self.num_points), dtype=int)

        for (s_idx, o_idx), data in self.data_grid.items():
            if data["card"] in self.cardinality_mask and data["forte"] not in ["Empty", "N/A"]:
                self.matrix_display[s_idx, o_idx] = self._get_forte_color_index(data["forte"])
            else:
                self.matrix_display[s_idx, o_idx] = 0

    def _init_ui(self):
        self.fig = plt.figure(figsize=(16, 10))


        self.fig.suptitle("Dynamic Multi-Scale Setscape Explorer ", fontsize=13, fontweight='bold',
                          x=0.5, ha='center')

        gs = self.fig.add_gridspec(5, 2, height_ratios=[3.0, 0.25, 1.8, 0.6, 0.8], width_ratios=[4, 2.2])

        self.ax_scape = self.fig.add_subplot(gs[0, 0])
        self.ax_scrollbar = self.fig.add_subplot(gs[1, 0])
        self.ax_piano = self.fig.add_subplot(gs[2, 0])

        self.ax_text = self.fig.add_subplot(gs[0:3, 1])

        self.ax_slider_max_scale = self.fig.add_subplot(gs[3, 0])
        self.ax_slider_step = self.fig.add_subplot(gs[4, 0])

        gs_controls_sub = gs[3:5, 1].subgridspec(3, 2, height_ratios=[2.2, 3.0, 1], width_ratios=[0.35, 0.65])
        self.ax_check = self.fig.add_subplot(gs_controls_sub[:, 0])
        self.ax_textbox = self.fig.add_subplot(gs_controls_sub[0, 1])
        self.ax_tools = self.fig.add_subplot(gs_controls_sub[1, 1])

        gs_btns_sub = gs_controls_sub[2, 1].subgridspec(1, 3)
        self.ax_btn_reset = self.fig.add_subplot(gs_btns_sub[0, 0])
        self.ax_btn_refresh = self.fig.add_subplot(gs_btns_sub[0, 1])
        self.ax_btn_file = self.fig.add_subplot(gs_btns_sub[0, 2])

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
        self.ax_scape.set_ylabel("Window Size / Scale (Offset)")
        self.ax_scape.set_xlabel("Actual Offset Position (Quarter Notes)")

        init_offset = self.offset_points[0]
        init_scale = self.scales[0]
        self.crosshair, = self.ax_scape.plot([init_offset], [init_scale], 'r+', markersize=14, markeredgewidth=2)

        self.slider_max_scale = Slider(
            ax=self.ax_slider_max_scale, label='Max Scale (Offset) ',
            valmin=2.0, valmax=self.total_length, valinit=self.max_scale_offset, valstep=1.0, dragging=False
        )
        self.slider_max_scale.on_changed(self._on_slider_release)

        self.slider_step = Slider(
            ax=self.ax_slider_step,
            label='Scale Step (Offset) ',
            valmin=0.1,
            valmax=16.0,
            valinit=self.offset_step,
            valstep=0.1,
            dragging=False
        )

        self.scrollbar = Slider(
            ax=self.ax_scrollbar, label='Pan View ',
            valmin=0.0, valmax=self.total_length, valinit=self.total_length / 2.0, color='lightgray'
        )
        self.scrollbar.on_changed(self._on_scroll_pan)

        labels = [str(i) for i in range(1, 13)]
        self.check_box = CheckButtons(self.ax_check, labels, [True] * 12)
        self.check_box.on_clicked(self._on_card_toggle)

        # 格式化文本
        base_name = os.path.basename(self.xml_path)
        corpus_display_text = format_corpus_two_lines(base_name)

        self.textbox_corpus = TextBox(self.ax_textbox, '', initial=corpus_display_text)

        if hasattr(self.textbox_corpus, 'text_disp'):
            self.textbox_corpus.text_disp.set_fontsize(9.0)
            self.textbox_corpus.text_disp.set_ha('left')
            self.textbox_corpus.text_disp.set_va('center')
            self.textbox_corpus.text_disp.set_position((0.05, 0.5))

        self.textbox_corpus.on_submit(self._on_corpus_submit)

        self.radio_tools = RadioButtons(
            self.ax_tools,
            ('Browse', 'Set Select', 'Zoom In (+)', 'Zoom Out (-)'),
            active=0
        )

        # 优化 RadioButtons 选项框内部的行距与字号（拉开底部 Zoom Out 的间距）
        if hasattr(self.radio_tools, 'circles') and hasattr(self.radio_tools, 'labels'):
            n_options = len(self.radio_tools.labels)
            # 使用更舒展的纵向间距分布，底部 Zoom Out 留出更多空白行距
            new_ys = np.array([0.88, 0.63, 0.38, 0.13])
            for i, (circle, label) in enumerate(zip(self.radio_tools.circles, self.radio_tools.labels)):
                y_pos = new_ys[i]
                circle.set_center((circle.center[0], y_pos))
                label.set_position((label.get_position()[0], y_pos))
                label.set_fontsize(5.5)

        self.radio_tools.on_clicked(self._on_tool_change)

        self.btn_reset = Button(self.ax_btn_reset, 'Reset')
        self.btn_reset.on_clicked(self._on_reset_view)

        # Refresh 刷新按钮
        self.btn_refresh = Button(self.ax_btn_refresh, 'Refresh', color='#E1D5E7', hovercolor='#D4B1D0')
        self.btn_refresh.on_clicked(self._on_refresh)

        self.btn_file = Button(self.ax_btn_file, 'Open File', color='lightblue', hovercolor='skyblue')
        self.btn_file.on_clicked(self._on_select_file)

        self.fig.canvas.mpl_connect('button_press_event', self._on_click)

        self._draw_base_piano_roll()

        self.rect_selector = RectangleSelector(
            self.ax_piano,
            self._on_piano_roll_2d_select,
            useblit=True,
            props=dict(alpha=0.3, facecolor='red', edgecolor='red', linewidth=1.5),
            interactive=True,
            drag_from_anywhere=True
        )
        self.rect_selector.set_active(False)

        self._update_window_overlay()
        self._update_text_info()
        plt.tight_layout()
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
        self.fig.canvas.draw_idle()

    def _analyze_custom_2d_range(self, start_offset, end_offset, min_pitch, max_pitch):
        pcs_sequence = []
        for note_tuple in self.piano_roll_notes:
            start, dur, pitch, _ = note_tuple
            end = start + dur
            if (start < end_offset and end > start_offset) and (min_pitch <= pitch <= max_pitch):
                pcs_sequence.append(pitch % 12)

        pcs_tuple, info = self._get_set_info(pcs_sequence)
        return {
            "pcs": list(pcs_tuple),
            "card": len(pcs_tuple),
            "forte": info['forte'],
            "prime": info['prime'],
            "iv": info['iv'],
            "start_offset": start_offset,
            "end_offset": end_offset,
            "min_pitch": min_pitch,
            "max_pitch": max_pitch
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
        self.fig.canvas.draw_idle()

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

        self.ax_scape.set_ylabel("Window Size / Scale (Offset)")
        self.ax_scape.set_xlabel("Actual Offset Position (Quarter Notes)")
        self.ax_scape.set_ylim(self.scales[0] - self.offset_step / 2, self.scales[-1] + self.offset_step / 2)

        if self.custom_2d_selection:
            cx = self.custom_2d_selection[0]
            cy = self.custom_2d_selection[1] - self.custom_2d_selection[0]
        else:
            cx = self.offset_points[self.selected_offset_idx]
            cy = self.scales[self.selected_scale_idx]

        self.crosshair, = self.ax_scape.plot([cx], [cy], 'r+', markersize=14, markeredgewidth=2)

    def _on_click(self, event):
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
                self._update_text_info()

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

                self.scrollbar.eventson = False
                self.scrollbar.set_val((new_xmin + new_xmax) / 2)
                self.scrollbar.eventson = True

            self.fig.canvas.draw_idle()

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

        self.rect_selector = RectangleSelector(
            self.ax_piano,
            self._on_piano_roll_2d_select,
            useblit=True,
            props=dict(alpha=0.3, facecolor='red', edgecolor='red', linewidth=1.5),
            interactive=True,
            drag_from_anywhere=True
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

        self.fig.canvas.draw_idle()

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
        """Render base Piano Roll visualization with multi-voice colored note rectangles."""
        self.ax_piano.clear()
        for pitch in range(self.min_midi, self.max_midi + 1):
            if pitch % 12 in [1, 3, 6, 8, 10]:
                self.ax_piano.axhspan(pitch - 0.5, pitch + 0.5, color='#f0f0f0', zorder=1)

        for note_tuple in self.piano_roll_notes:
            start, dur, pitch, voice_id = note_tuple
            color_idx = voice_id % len(self.voice_colors)
            face_color = self.voice_colors[color_idx]

            rect = patches.Rectangle(
                (start, pitch - 0.4), dur, 0.8,
                linewidth=0.5, edgecolor='#333333',
                facecolor=face_color, alpha=0.8, zorder=2
            )
            self.ax_piano.add_patch(rect)

        self.ax_piano.set_xlim(0, self.total_length)
        self.ax_piano.set_ylim(self.min_midi - 1, self.max_midi + 1)
        self.ax_piano.set_ylabel("MIDI Pitch")
        self.ax_piano.set_xlabel("Offset Position")
        self.window_patch = None

    def _update_window_overlay(self):
        self._remove_window_overlay()

        if self.custom_2d_selection:
            start_o, end_o, ymin, ymax = self.custom_2d_selection
            width = end_o - start_o
            height = ymax - ymin

            self.window_patch = patches.Rectangle(
                (start_o, ymin), width, height,
                linewidth=1.5, edgecolor='red', facecolor='red', alpha=0.25, zorder=3
            )
            title_str = f"Piano Roll View | Active Window: {start_o:.2f} to {end_o:.2f} (MIDI: {ymin:.1f}-{ymax:.1f})"
        else:
            info = self.data_grid[(self.selected_scale_idx, self.selected_offset_idx)]
            start_o, end_o = info["start_offset"], info["end_offset"]

            self.window_patch = patches.Rectangle(
                (start_o, self.min_midi - 1), end_o - start_o, (self.max_midi - self.min_midi + 2),
                linewidth=1.5, edgecolor='red', facecolor='red', alpha=0.25, zorder=3
            )
            title_str = f"Piano Roll View | Active Window: {start_o:.2f} to {end_o:.2f} (Full Pitch)"

        self.ax_piano.add_patch(self.window_patch)
        self.ax_piano.set_title(title_str, fontsize=10, loc='left')

    def _on_slider_release(self, val):
        self.max_scale_offset = self.slider_max_scale.val
        self.slider_step.set_val(self.slider_step.val)

    def _on_refresh(self, event):
        """点击 Refresh 按钮后，根据当前的滑块数值重新计算网格并刷新图表"""
        print("Refreshing visualization and recalculating data grid...")
        self.max_scale_offset = self.slider_max_scale.val
        self.offset_step = self.slider_step.val

        self._recompute_data_grid()
        self._update_matrix()

        self.selected_offset_idx = min(self.selected_offset_idx, self.num_points - 1)
        self.selected_scale_idx = min(self.selected_scale_idx, self.num_scales - 1)

        self._redraw_setscape_pcolormesh()
        self._update_window_overlay()
        self._update_text_info()
        self.fig.canvas.draw_idle()

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

        self.fig.canvas.draw_idle()

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
        self.fig.canvas.draw_idle()

    def _on_card_toggle(self, label):
        card = int(label)
        if card in self.cardinality_mask:
            self.cardinality_mask.remove(card)
        else:
            self.cardinality_mask.add(card)

        self._update_matrix()
        self.quad_mesh.set_array(self.matrix_display.ravel())
        self.fig.canvas.draw_idle()

    def _update_text_info(self):
        """Update analysis info and dynamically render colored visual swatches for voices in the right panel without overflow."""
        self.ax_text.clear()

        self.ax_text.set_xticks([])
        self.ax_text.set_yticks([])
        self.ax_text.set_facecolor('#FFFDF5')
        for spine in self.ax_text.spines.values():
            spine.set_visible(True)
            spine.set_color('#C0C0C0')
            spine.set_linewidth(1.0)

        if self.custom_2d_selection:
            x1, x2, y1, y2 = self.custom_2d_selection
            info = self._analyze_custom_2d_range(x1, x2, y1, y2)
            window_sz = x2 - x1
            pitch_str = f"\nPitch: {y1:.1f}-{y2:.1f}"
        else:
            info = self.data_grid.get((self.selected_scale_idx, self.selected_offset_idx), None)
            window_sz = self.scales[self.selected_scale_idx] if info else 0.0
            pitch_str = ""

        if info:
            text_str = (
                f"Mode: [{self.active_tool}]\n"
                f"Offset: {info['start_offset']:.1f}-{info['end_offset']:.1f}{pitch_str}\n"
                f"Window: {window_sz:.1f} | Step: {self.offset_step:.1f}\n"
                f"Forte: {info['forte']}\n"
                f"Prime: {info['prime']}\n"
                f"PCs: {info['pcs']}\n"
                f"IV: {info['iv']}\n"
                f"Card: {info['card']}"
            )
        else:
            text_str = "No Data Selected"

        self.ax_text.text(
            0.05, 0.95, text_str,
            transform=self.ax_text.transAxes,
            fontsize=8,
            verticalalignment='top',
            fontfamily='monospace'
        )

        y_cursor = 0.44
        self.ax_text.text(
            0.05, y_cursor, "--- Voices / Parts ---",
            transform=self.ax_text.transAxes,
            fontsize=8,
            fontweight='bold',
            verticalalignment='top',
            fontfamily='monospace',
            color='#333333'
        )

        y_cursor -= 0.045
        if self.voice_legend:
            for v_id, v_info in self.voice_legend.items():
                display_name = v_info['name']
                if len(display_name) > 20:
                    display_name = display_name[:18] + ".."

                self.ax_text.text(
                    0.05, y_cursor, f"█  {display_name}",
                    transform=self.ax_text.transAxes,
                    fontsize=8,
                    color=v_info['color'],
                    fontweight='bold',
                    verticalalignment='top',
                    fontfamily='monospace'
                )
                y_cursor -= 0.038
        else:
            self.ax_text.text(
                0.05, y_cursor, "No Voice Info",
                transform=self.ax_text.transAxes,
                fontsize=8,
                verticalalignment='top',
                fontfamily='monospace',
                color='#666666'
            )


if __name__ == "__main__":
    explorer = InteractiveDynamicSetExplorer()