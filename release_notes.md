## Twelve-Tone Music Analyzer v1.4.1

### ✨ New Features
- **Merge Parts & Measures Search** — select arbitrary parts and bar ranges, merge all notes into a chronological PC sequence, find complete 12-tone rows, and match against confirmed row forms (P/I/R/RI)
- **Per-bar part breakdown** shows each voice's pitch classes, Forte class, and unique PCs per measure
- **Per-part unique PC display** grouped horizontally for quick cross-voice comparison
- **Row form matching** — merged 12-PC sequence is checked against all 48 forms of the confirmed row

### 🔧 Improvements
- Merged PC sequence now sorted by bar → offset for correct chronological order
- Unique PCs displayed in appearance order (not sorted by pitch class value)
- 48-form subset search uses correct inversion formula: `(2×pivot − p) % 12` matching the matrix calculation
- Form labels now show the correct transposition number based on each form's starting pitch

### 🐛 Bug Fixes
- Fixed circular import between `i18n.py` and `score_opener.py`
- Fixed `QCheckBox` and `music21.chord` missing imports in twelve_tone_tab.py
- Fixed I/RI form calculation in Subset Search (was using wrong inversion axis)

### 📦 Installers

| Platform | File | Size |
|----------|------|------|
| 🍎 macOS | `TwelveToneAnalyzer_Setup_v1.4.1.dmg` | ~212 MB |
| 🪟 Windows | `TwelveToneAnalyzer_Setup_v1.4.1.exe` | |
| 📦 Windows Portable | `TwelveToneAnalyzer_Portable_v1.4.1.zip` | |
