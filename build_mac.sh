#!/bin/bash
# ============================================================
#  TwelveToneAnalyzer — macOS build script
#
#  Usage:
#    chmod +x build_mac.sh
#    ./build_mac.sh          → build .app
#    ./build_mac.sh dmg      → build .app + .dmg installer
# ============================================================
set -e

APP_NAME="TwelveToneAnalyzer"
DMG_NAME="TwelveToneAnalyzer_Setup_v1.4.1"
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
cd "$SCRIPT_DIR"

echo "=========================================="
echo "  TwelveToneAnalyzer — macOS Build"
echo "=========================================="

# ---- 1. Check Python ----
PYTHON="python3"
if ! command -v "$PYTHON" &>/dev/null; then
    echo "[ERROR] python3 not found. Install Python 3.9+ from python.org"
    exit 1
fi
echo "[INFO] Python: $($PYTHON --version)"

# ---- 2. Create / activate venv ----
VENV=".venv_mac"
if [ ! -f "$VENV/bin/python" ]; then
    echo "[INFO] Creating virtual environment: $VENV"
    $PYTHON -m venv "$VENV"
fi
source "$VENV/bin/activate"
echo "[INFO] Virtual env activated"

# ---- 3. Install dependencies ----
echo "[INFO] Installing dependencies..."
pip install --upgrade pip -q
pip install PyInstaller -q
pip install -r requirements_mac.txt -q
echo "[INFO] Dependencies installed"

# ---- 4. Convert icon if needed ----
ICNS="app_icon.icns"
if [ ! -f "$ICNS" ] && [ -f "app_icon.ico" ]; then
    echo "[INFO] No .icns icon found. Create one from PNG (or skip)."
    echo "       Place a 1024x1024 PNG at app_icon.png and re-run."
    echo "       (Icon will be skipped — app will use default)"
fi

# ---- 5. Clean old builds ----
echo "[INFO] Cleaning old builds..."
rm -rf build/ "$APP_NAME" dist/"$APP_NAME" dist/"$APP_NAME".app 2>/dev/null || true

# ---- 6. Build .app bundle ----
echo "[INFO] Building .app bundle with PyInstaller..."
pyinstaller TwelveToneAnalyzer_mac.spec
echo "[INFO] Build complete!"

echo ""
echo "=========================================="
echo "  .app bundle ready:"
echo "  dist/$APP_NAME.app"
echo "=========================================="

# ---- 7. Check — run the app to verify ----
if [ -d "dist/$APP_NAME.app" ]; then
    echo "[INFO] To test: open dist/$APP_NAME.app"
    # open "dist/$APP_NAME.app"
fi

# ---- 8. Package as .dmg ----
if [ "$1" = "dmg" ]; then
    echo ""
    echo "[INFO] Creating .dmg installer..."

    DMG_DIR="dist/dmg_staging"
    rm -rf "$DMG_DIR"
    mkdir -p "$DMG_DIR"

    # Copy .app into staging
    cp -R "dist/$APP_NAME.app" "$DMG_DIR/"

    # Create symlink to /Applications for drag-to-install
    ln -s /Applications "$DMG_DIR/Applications"

    # Create .dmg with hdiutil
    DMG_FILE="dist/${DMG_NAME}.dmg"
    rm -f "$DMG_FILE"

    hdiutil create \
        -volname "$APP_NAME" \
        -srcfolder "$DMG_DIR" \
        -ov -format UDZO \
        "$DMG_FILE"

    # Clean staging
    rm -rf "$DMG_DIR"

    echo ""
    echo "=========================================="
    echo "  .dmg installer ready:"
    echo "  $DMG_FILE"
    echo "=========================================="
    echo ""
    echo "  User experience:"
    echo "    1. Double-click .dmg to mount"
    echo "    2. Drag $APP_NAME.app → Applications"
    echo "    3. Launch from Applications / Launchpad"
    echo ""
fi

echo ""
echo "Done!"
