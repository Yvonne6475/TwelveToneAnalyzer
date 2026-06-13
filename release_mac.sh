#!/bin/bash
# ============================================================
#  TwelveToneAnalyzer — One-click release script (macOS)
#
#  Usage:
#    chmod +x release_mac.sh
#    ./release_mac.sh                       → rebuild .app + .dmg
#    ./release_mac.sh 1.2                   → bump version + rebuild
#    ./release_mac.sh 1.2 "fix: crash on open" → bump + rebuild + git push
# ============================================================
set -e

APP_NAME="TwelveToneAnalyzer"
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
cd "$SCRIPT_DIR"

RED='\033[0;31m'; GREEN='\033[0;32m'; YELLOW='\033[1;33m'
CYAN='\033[0;36m'; NC='\033[0m'

echo -e "${CYAN}============================================"
echo -e "  $APP_NAME — Release Builder (macOS)"
echo -e "============================================${NC}"
echo ""

VERSION="$1"
MESSAGE="$2"

# ---- 1. Check Python ----
echo -e "${YELLOW}[1/6] Checking Python...${NC}"
if ! command -v python3 &>/dev/null; then
    echo -e "${RED}[ERROR] python3 not found. Install from python.org${NC}"
    exit 1
fi
PYTHON="$(command -v python3)"
echo -e "${GREEN}        Python: $($PYTHON --version)${NC}"

# ---- 2. Create/activate venv ----
echo -e "${YELLOW}[2/6] Setting up virtual environment...${NC}"
VENV=".venv_mac"
if [ ! -f "$VENV/bin/python" ]; then
    $PYTHON -m venv "$VENV"
fi
source "$VENV/bin/activate"
pip install --upgrade pip -q 2>/dev/null
pip install PyInstaller -q 2>/dev/null
pip install -r requirements_mac.txt -q 2>/dev/null
echo -e "${GREEN}        Virtual env ready${NC}"

# ---- 3. Bump version ----
if [ -n "$VERSION" ]; then
    echo -e "${YELLOW}[3/6] Bumping version to $VERSION ...${NC}"

    # installer.nsi
    if [ -f installer.nsi ]; then
        sed -i '' "s/!define VERSION \".*\"/!define VERSION \"$VERSION\"/" installer.nsi
    fi

    # i18n.py
    sed -i '' "s/v[0-9]\+\.[0-9]\+/v$VERSION/g" src/utils/i18n.py

    # build_mac.sh
    sed -i '' "s/DMG_NAME=\"TwelveToneAnalyzer_Setup_v[0-9.]*\"/DMG_NAME=\"TwelveToneAnalyzer_Setup_v$VERSION\"/" build_mac.sh

    # release.ps1 (Windows counterpart)
    if [ -f release.ps1 ]; then
        sed -i '' "s/!define VERSION \".*\"/!define VERSION \"$VERSION\"/" release.ps1 2>/dev/null || true
    fi

    echo -e "${GREEN}        Version bumped to $VERSION${NC}"
else
    echo -e "${YELLOW}[3/6] Version: unchanged (pass version as arg: ./release_mac.sh 1.2)${NC}"
fi

# ---- 4. Clean & Build ----
echo -e "${YELLOW}[4/6] Cleaning old builds...${NC}"
rm -rf build/ dist/ 2>/dev/null || true
echo -e "${GREEN}        Cleaned${NC}"

echo -e "${YELLOW}[5/6] Building .app + .dmg...${NC}"
pyinstaller TwelveToneAnalyzer_mac.spec 2>&1 | tail -3

if [ ! -d "dist/$APP_NAME.app" ]; then
    echo -e "${RED}[ERROR] .app build failed!${NC}"
    exit 1
fi
echo -e "${GREEN}        .app built${NC}"

# Package as .dmg
DMG_DIR="dist/dmg_staging"
rm -rf "$DMG_DIR"
mkdir -p "$DMG_DIR"
cp -R "dist/$APP_NAME.app" "$DMG_DIR/"
ln -s /Applications "$DMG_DIR/Applications"

DMG_FILE="dist/TwelveToneAnalyzer_Setup_v${VERSION:-1.1}.dmg"
rm -f "$DMG_FILE"
hdiutil create -volname "$APP_NAME" -srcfolder "$DMG_DIR" -ov -format UDZO "$DMG_FILE" 2>&1 | tail -1
rm -rf "$DMG_DIR"

DMG_SIZE=$(du -sh "$DMG_FILE" | cut -f1)
echo -e "${GREEN}        .dmg built ($DMG_SIZE)${NC}"

# ---- 6. Git commit & push ----
echo -e "${YELLOW}[6/6] Git...${NC}"
if [ -n "$MESSAGE" ]; then
    git add .
    git commit -m "$MESSAGE"
    git push
    echo -e "${GREEN}        Committed & pushed to GitHub${NC}"
elif [ -n "$VERSION" ]; then
    git add .
    git commit -m "release: v$VERSION"
    git push
    echo -e "${GREEN}        Committed & pushed to GitHub${NC}"
else
    echo -e "${YELLOW}        Skipped (no message provided)${NC}"
fi

# ---- Done ----
echo ""
echo -e "${CYAN}============================================"
echo -e "  Release Complete!"
echo -e "============================================${NC}"
echo ""
echo -e "  .app:  dist/$APP_NAME.app"
echo -e "  .dmg:  $DMG_FILE"
echo ""
echo -e "  User install: double-click .dmg → drag to Applications"
echo ""
