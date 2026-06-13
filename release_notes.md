## Twelve-Tone Music Analyzer v1.2

### 🐛 Fixes
- **Fixed twelve-tone matrix heatmap axis labels**: top columns now consistently show P0–P11 (prime forms), left rows now consistently show I0–I11 (inversions)
- **Fixed MEI parser bug**: `cleaned` variable initialization in beam/tuplet stripping loop
- **Fixed music21 corpus path resolution** in PyInstaller builds (now uses bundled `_internal/music21` directory)

### ✨ New Features
- **ABC format support** (`.abc` files) — import folk/traditional music scores
- **Humdrum/\*\*kern format support** (`.krn` files) — import musicology research scores
- **Pre-install running-process detection**: installer now warns if `TwelveToneAnalyzer.exe` is already running
- **Default install path** changed to `D:\Twelve-Tone Music Analyzer` to avoid `C:\Program Files` permission issues

### 📦 Installers

| Platform | File | Size |
|----------|------|------|
| 🪟 Windows | `TwelveToneAnalyzer_Setup_v1.2.exe` | ~171 MB |
| 🍎 macOS | `TwelveToneAnalyzer_Setup_v1.2.dmg` | — |

### 🪟 Windows
1. Run `TwelveToneAnalyzer_Setup_v1.2.exe` (requires administrator privileges)
2. Follow the setup wizard — default installs to `D:\Twelve-Tone Music Analyzer`
3. Launch from the desktop shortcut
4. If upgrading from v1.1, uninstall the old version first

### 🍎 macOS
1. Double-click `TwelveToneAnalyzer_Setup_v1.2.dmg` to mount
2. Drag `TwelveToneAnalyzer.app` to `Applications`
3. Launch from Launchpad or Applications

### Features
- Twelve-tone matrix analysis with heatmap
- Forte set classification
- Chord analysis (trichords / tetrachords / hexachords)
- Audio analysis (librosa)
- Score visualization (music21)
- Inclusion lattice
- ABC and Humdrum format import

Built with PyInstaller + NSIS | Windows 10+ / macOS 10.15+
