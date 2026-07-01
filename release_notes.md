## Twelve-Tone Music Analyzer v1.4.0

### ✨ New Features
- **Row Division Dialog** — standalone popup window with adjustable group size (1–12), replaces the old collapsible panel
- **48-Form Subset Search** — input a pitch-class set and search all 48 transformations (P₀–P₁₁, I₀–I₁₁, R₀–R₁₁, RI₀–R₁₁) for consecutive matches (min. 3 notes)
- **"Get from Chords Analysis" now shows per-chord bar numbers & part names** in Set Relations, Lattice, and Forte Set Analysis
- **Merged set display** — merged (bar-union) chords shown in Chord Analysis table with yellow background, constituent chord info, and part/voice details
- **Chord Analysis Markdown export includes per-bar merged rows** with constituent chord breakdown
- **Prime Form column** added to Chord Analysis table and Markdown/CSV export

### 🔧 Improvements
- **Chord annotation format**: pitch classes → note names, grouped by pitch height (highest first)
- **Chords PCs column**: renamed from "Normal Order", now sorted by MIDI pitch descending
- **Normal Order column**: kept as standard Forte ascending compact form
- **Intervals now calculated from Chords PCs order** (MIDI-descending) in Set Relations
- **All analysis buttons now open standalone dialogs** (Row Division, Subset Search)
- **Set Relations results**: includes Prime Form, Intervals, Normal Order, and bar/part info on every item
- **Deduplication**: Supersets, Subsets, Z/K relations, Invariants all deduplicated in Set Relations
- **Single-note sets filtered out** from all "Get from Chords Analysis" imports
- **Selectable/copyable results text** in Set Relations tab
- **Merge labels with constituent info**: `[merged Bar 12: [6,9,11](Violin I) + [0,4,7](Viola)]`

### 🐛 Fixes
- **Forte Set Analysis dialog** now properly shows part/voice info for each chord
- **Cursor stuck as WaitCursor after extraction** — fixed with forced cursor reset in try/finally
- **Duplicate entries in Set Relations results** — deduplication added to all result sections
- **Part name truncation in Chord Analysis table** — enabled word wrap and multi-line support
- **Row Division dialog class not defined** — missing class definitions properly inserted

### 📦 Installers

| Platform | File | Size |
|----------|------|------|
| 🍎 macOS | `TwelveToneAnalyzer_Setup_v1.4.0.dmg` | ~212 MB |

### 🍎 macOS
1. Double-click `TwelveToneAnalyzer_Setup_v1.4.0.dmg` to mount
2. Drag `TwelveToneAnalyzer.app` to `Applications`
3. Launch from Launchpad or Applications
