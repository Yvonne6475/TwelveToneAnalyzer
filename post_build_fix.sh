#!/bin/bash
# ============================================================
# PyInstaller 6.20.0 + Python 3.9.6 macOS workarounds
#
# PyInstaller's BUNDLE step on Apple Silicon misses:
#   1. base_library.zip (Python stdlib)
#   2. Python shared library symlink (bootloader expects
#      Frameworks/Python)
#   3. Qt framework @rpath symlinks
#   4. Embedded .dylib @rpath symlinks
#
# This script patches the .app bundle after `pyinstaller` runs.
# ============================================================
set -e

APP="${1:-dist/TwelveToneAnalyzer.app}"
BUILD_DIR="${2:-build/TwelveToneAnalyzer_mac}"

if [ ! -d "$APP" ]; then
    echo "Usage: $0 <app_bundle_path> [build_dir]"
    echo "  app_bundle_path — e.g. dist/TwelveToneAnalyzer.app"
    echo "  build_dir       — e.g. build/TwelveToneAnalyzer_mac"
    exit 1
fi

FW="$APP/Contents/Frameworks"

echo "[post_build_fix] Patching $APP ..."

# 1. Copy base_library.zip
if [ -f "$BUILD_DIR/base_library.zip" ] && [ ! -f "$FW/base_library.zip" ]; then
    cp "$BUILD_DIR/base_library.zip" "$FW/"
    echo "  ✓ base_library.zip"
fi

# 2. Python symlink (bootloader looks for Frameworks/Python)
PYTHON_FW=$(find "$FW" -name "Python.framework" -type d -maxdepth 2 2>/dev/null | head -1)
if [ -n "$PYTHON_FW" ]; then
    PYTHON_LIB="$PYTHON_FW/Versions/3.9/Python"
    if [ -f "$PYTHON_LIB" ] && [ ! -L "$FW/Python" ]; then
        REL=$(python3 -c "import os.path; print(os.path.relpath('$PYTHON_LIB', '$FW'))")
        ln -sf "$REL" "$FW/Python"
        echo "  ✓ Python symlink → $REL"
    fi
fi

# 3. Qt framework @rpath symlinks
QT_LIB="$FW/PyQt5/Qt5/lib"
if [ -d "$QT_LIB" ]; then
    count=0
    for fw in "$QT_LIB"/*.framework; do
        name=$(basename "$fw" .framework)
        target="PyQt5/Qt5/lib/${name}.framework/Versions/5/${name}"
        if [ -f "$FW/$target" ] && [ ! -e "$FW/$name" ]; then
            ln -sf "$target" "$FW/$name"
            ((count++)) || true
        fi
    done
    echo "  ✓ Qt symlinks ($count frameworks)"
fi

# 4. Embedded .dylib @rpath symlinks (PIL, scipy, etc.)
dylib_count=0
find "$FW" -name "*.dylib" -type f 2>/dev/null | while read dylib; do
    name=$(basename "$dylib")
    relpath="${dylib#$FW/}"
    if [ ! -e "$FW/$name" ]; then
        ln -sf "$relpath" "$FW/$name"
        echo "  + $name"
    fi
done

# 5. Re-sign ad-hoc
echo "  Re-signing..."
codesign --force --deep --sign - "$APP" 2>&1 | grep -v "^$" || true

echo "[post_build_fix] Done."
