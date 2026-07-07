## Twelve-Tone Music Analyzer v1.4.2

### 🔧 Improvements
- **Disabled windowed traceback** — crashes show a friendly dialog instead of a console window
- **Windows default install path** changed to `%PROGRAMFILES64%` (was `D:\`)
- **URL prompts** simplified to `.wav` format examples
- **Audio URL dialog** now shows placeholder text

### 🐛 Bug Fixes
- **Windows "Error loading Python DLL"** — `python39.dll` now explicitly bundled in the executable directory
- **Windows build size reduced** — test directories (`/tests/`, `/test_data/`, `/examples/`) excluded from scipy/numpy/matplotlib, saving ~500MB
- **VC++ Runtime check** — NSIS installer now detects missing VC++ redistributable and warns the user
- **Portable ZIP** now excludes `.pyc` and `__pycache__`

### 📦 Installers

| Platform | File |
|----------|------|
| 🍎 macOS | `TwelveToneAnalyzer_Setup_v1.4.2.dmg` |
| 🪟 Windows | `TwelveToneAnalyzer_Setup_v1.4.2.exe` |
| 📦 Windows Portable | `TwelveToneAnalyzer_Portable_v1.4.2.zip` |
