## Twelve-Tone Music Analyzer v1.3.3.2

### 🐛 Fixes
- **Fixed plot rendering errors**: forced matplotlib Qt5Agg backend before PyQt5 imports; all music21 plot() calls now use `doneAction=None` + `figure.show()` to avoid external viewer launch errors
- **Fixed PDF export Permission denied**: temp directory now validates writability with fallback to `~/MusicAnalysisTemp`; `configure_music21_environment()` syncs music21 scratch dir before every PDF export
- **URL downloads use original filenames**: replaced MD5 hash naming with `suggested_filename_from_url()`; download prompts save-as dialog before starting transfer
- **All export dialogs default to temp directory**: instead of Desktop or empty string, exports now suggest the user's configured temp directory
- **Fixed music21.serial import in frozen app**: `create_12tone_matrix` now uses deferred import to avoid `NameError` in PyInstaller builds
- **macOS font fallback warnings eliminated**: uses Helvetica Neue on macOS instead of Segoe UI (70ms+ fallback overhead)
- **Fixed missing `load_language` import** in language selection dialog

### ✨ New Features
- **P / I / R / RI transformation analysis** — Forte Name dialog now computes Prime, Inversion, Retrograde, and Retrograde-Inversion forms for each pitch-class set
- **P/I/R/RI match search in Set Relations** — searches the entire universe for sets matching target transformations
- **Chord Relation Lattice** — build inclusion lattices directly from extracted chord analysis sets
- **Adaptive node sizing & spacing** in inclusion lattice — prevents label overlap for long pitch-class names
- **Golden-ratio edge coloring** in lattice — adjacent parent nodes get maximally distinct colors via tab20 colormap
- **Straight-line edges with arrows** for clearer inclusion relationship display
- **Interval Vector display** across Forte Name dialog and Set Relations tab
- **Consecutive interval display** in Normal Order results
- **A=10, B=11 musicology convention hint** in twelve-tone matrix
- **Expanded lattice size range** (1–11) with large-span warning
- **First-launch language selection dialog**
- **Collapsible panel** and auto-updater support

### 📦 Installers

| Platform | File | Size |
|----------|------|------|
| 🍎 macOS | `TwelveToneAnalyzer_Setup_v1.3.2.dmg` | ~212 MB |

### 🍎 macOS
1. Double-click `TwelveToneAnalyzer_Setup_v1.3.2.dmg` to mount
2. Drag `TwelveToneAnalyzer.app` to `Applications`
3. Launch from Launchpad or Applications

### Features
- Twelve-tone matrix analysis with heatmap
- P / I / R / RI transformation computation
- Forte set classification with interval vectors
- Chord analysis (trichords / tetrachords / hexachords)
- Inclusion lattice with adaptive visualization
- Chord Relation Lattice
- Set relations (subsets, supersets, Z/K relations, nexus, transformations)
- Audio analysis (librosa)
- Score visualization (music21)
- ABC and Humdrum format import

Built with PyInstaller | macOS 10.15+
