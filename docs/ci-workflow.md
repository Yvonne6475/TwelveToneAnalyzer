---
name: tma-dmg-to-exe-workflow
description: "Working GitHub Actions CI/CD — macOS DMG + Windows EXE with NSIS ZLIB, 6 iterations to get right"
metadata: 
  node_type: memory
  type: reference
  originSessionId: a8bc4b64-2e88-4ef7-8760-65adb505d738
---

# TwelveToneAnalyzer GitHub Actions CI/CD — macOS DMG + Windows EXE

## Pipeline Overview

```
push tag vX.Y.Z
     │
     ├── macos-latest ── pip install ── pyinstaller (.app) ── hdiutil (.dmg) ──┐
     │                                                                         │
     ├── windows-latest ─ pip install ── pyinstaller (.exe) ── NSIS (ZLIB) ──┤
     │                                                                         │
     └── ubuntu-latest ── download artifacts ── gh-release ──────────────────┘
```

Triggers: `push` to master, `tags: ['v*']`, `workflow_dispatch`.

## Key Files

| File | Purpose |
|------|---------|
| `.github/workflows/build.yml` | CI pipeline (macOS + Windows + Release) |
| `TwelveToneAnalyzer_mac.spec` | PyInstaller macOS spec (scipy collect_all, app icon, plist) |
| `TwelveToneAnalyzer.spec` | PyInstaller Windows spec (Qt DLL filter, scipy collect_all) |
| `installer.nsi` | NSIS Windows installer (ZLIB, File /r, Modern UI) |
| `requirements_mac.txt` | macOS deps (includes PyInstaller) |
| `requirements.txt` | Windows deps (PyInstaller installed separately in CI) |
| `src/core/updater.py` | VERSION constant — single source of truth |

## 6 Iterations to Get Right

| # | Problem | Root Cause | Fix |
|---|---------|------------|-----|
| 1 | Windows build crashed | `Analysis(optimize=0)` not supported in PyInstaller 5.13.2 | Remove `optimize=` from `.spec` |
| 2 | `makensis: command not found` | NSIS not on Windows runner | `choco install nsis -y` |
| 3 | `makensis` still not found | PATH with spaces (`C:\Program Files (x86)`) | Use pwsh absolute path |
| 4 | `!define VERSION already defined` | NSIS hardcode + CI `/DVERSION=` conflict | Comment out `!define VERSION` in .nsi, only CLI `/DVERSION=` |
| 5 | `No files found` for artifact upload | NSIS outputs to root, not `dist/` | `Move-Item -Force` to `dist/` after NSIS |
| 6 | "Extraction failed (code 1)" on install | PowerShell Expand-Archive fails on large zip | Replace zip+extract with NSIS `File /r` directly |

## Windows NSIS Key Decisions

**ZLIB over LZMA** — ZLIB decompresses 2-3x faster, install time matters more than ~10% file size.

**File /r over zip+PowerShell** — NSIS `File /r` recursively includes the COLLECT output directly. No intermediate zip, no PowerShell extraction. Much more reliable.

**VERSION from CI only** — `!define VERSION` is commented out in .nsi. CI injects via `makensis /DVERSION="x.y.z"`. Avoids "already defined" error.

**CRCCheck off** — Disables per-file CRC, speeds up installer startup.

**Default install to D:\** — Avoids C:\ permission issues, user can change.

## Spec File Must-Haves

```python
# Both specs need scipy collect_all for C extensions like _cdflib
for _pkg in ('PyQt5', 'music21', 'scipy'):
    _ret = collect_all(_pkg)
    datas += _ret[0]; binaries += _ret[1]; hiddenimports += _ret[2]
```

## music21 MuseScore Path

In `main.py`, before any music21 imports, configure:
```python
from music21 import environment
from src.utils.config import get_musescore_path
_ms = get_musescore_path()
if _ms:
    _env = environment.Environment()
    _env['musicxmlPath'] = _ms
    _env['musescoreDirectPNGPath'] = _ms
```

This ensures `excerpt.write('musicxml.pdf', ...)` works in frozen app.

## Release Process

```bash
# 1. Bump version in src/core/updater.py (and build_mac.sh, _mac.spec)
# 2. Commit, tag, push
git tag v1.3.5
git push origin v1.3.5
# 3. Wait ~12 min → Release auto-created on GitHub
```

## Related

[[codebase-overview]] — TwelveToneAnalyzer project structure
[[project_context_cost]] — prefer high-signal reads
