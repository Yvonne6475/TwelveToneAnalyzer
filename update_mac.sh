#!/bin/bash
# ============================================================
#  TwelveToneAnalyzer — macOS Interactive Update Script
#
#  Run after making code changes.  Asks:
#    1. Continue modifying?  (Y → exit and modify, then re-run)
#    2. Rebuild .app / .dmg? (runs build_mac.sh, optional version bump)
#    3. Upload to GitHub?    (git add/commit/push)
#
#  After git pull, this script detects new upstream changes
#  and prompts to rebuild the .dmg package.
#
#  Usage:
#    chmod +x update_mac.sh
#    ./update_mac.sh
# ============================================================
set -e

APP_NAME="TwelveToneAnalyzer"
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
cd "$SCRIPT_DIR"

echo ""
echo "============================================"
echo "  $APP_NAME — Update Script (macOS)"
echo "============================================"
echo ""

# ═══════════════════════════════════════════════════════════════
# Pre-check: detect if we just pulled new changes from GitHub.
# ═══════════════════════════════════════════════════════════════
NEW_CHANGES=false
if git rev-parse --git-dir >/dev/null 2>&1; then
    # Fetch the latest without merging
    git fetch origin 2>/dev/null || true

    LOCAL=$(git rev-parse HEAD 2>/dev/null || echo "")
    REMOTE=$(git rev-parse origin/master 2>/dev/null || git rev-parse origin/main 2>/dev/null || echo "")

    if [ -n "$LOCAL" ] && [ -n "$REMOTE" ] && [ "$LOCAL" != "$REMOTE" ]; then
        NEW_CHANGES=true
        echo "[!] New changes detected from GitHub (upstream has new commits)."
        echo "    Local : ${LOCAL:0:7}"
        echo "    Remote: ${REMOTE:0:7}"
        echo ""
    fi
fi

# ═══════════════════════════════════════════════════════════════
# Step 1 — Continue modifying?
# ═══════════════════════════════════════════════════════════════
read -p "[1/4] Do you want to continue modifying code? [Y/N]: " CONTINUE
if [[ "$CONTINUE" =~ ^[Yy] ]]; then
    echo ""
    echo "    OK, make your changes. When done, run:"
    echo "      ./update_mac.sh"
    echo ""
    exit 0
fi

echo "    Proceeding with update workflow..."
echo ""

# ═══════════════════════════════════════════════════════════════
# Step 2 — Rebuild .app / .dmg?
# ═══════════════════════════════════════════════════════════════
VERSION_BUMPED=false
NEW_VERSION=""

# If new upstream changes were detected, nudge the user
if $NEW_CHANGES; then
    echo "    [!] Upstream changes detected — rebuilding .dmg is recommended."
fi

read -p "[2/4] Rebuild .app / .dmg? [Y/N]: " DO_BUILD

if [[ "$DO_BUILD" =~ ^[Yy] ]]; then
    # --- Optional version bump ---
    read -p "    Enter new version (press Enter to skip): " NEW_VERSION
    if [ -n "${NEW_VERSION// /}" ]; then
        echo "    Bumping version to v$NEW_VERSION ..."

        # macOS: TwelveToneAnalyzer_mac.spec
        if [ -f "TwelveToneAnalyzer_mac.spec" ]; then
            sed -i '' "s/'CFBundleShortVersionString': '[0-9.]*'/'CFBundleShortVersionString': '$NEW_VERSION'/" \
                TwelveToneAnalyzer_mac.spec
            sed -i '' "s/'CFBundleVersion': '[0-9.]*'/'CFBundleVersion': '${NEW_VERSION}.0'/" \
                TwelveToneAnalyzer_mac.spec
            echo "      TwelveToneAnalyzer_mac.spec updated"
        fi

        # macOS: build_mac.sh (DMG_NAME)
        if [ -f "build_mac.sh" ]; then
            sed -i '' "s/DMG_NAME=\"TwelveToneAnalyzer_Setup_v[0-9.]*\"/DMG_NAME=\"TwelveToneAnalyzer_Setup_v$NEW_VERSION\"/" \
                build_mac.sh
            echo "      build_mac.sh updated (DMG name)"
        fi

        # Cross-platform: installer.nsi
        if [ -f "installer.nsi" ]; then
            sed -i '' "s/!define VERSION \"[0-9.]*\"/!define VERSION \"$NEW_VERSION\"/" \
                installer.nsi
            echo "      installer.nsi updated (Windows)"
        fi

        # Cross-platform: i18n.py
        if [ -f "src/utils/i18n.py" ]; then
            sed -i '' "s/v[0-9.]\+/v$NEW_VERSION/" \
                src/utils/i18n.py
            echo "      src/utils/i18n.py updated"
        fi

        VERSION_BUMPED=true
    fi

    # --- Run build_mac.sh ---
    echo "    Building .app bundle..."

    # Determine build target
    BUILD_TARGET=""
    read -p "    Also create .dmg installer? [Y/N]: " DO_DMG
    if [[ "$DO_DMG" =~ ^[Yy] ]]; then
        BUILD_TARGET="dmg"
    fi

    if [ -x "build_mac.sh" ]; then
        bash build_mac.sh $BUILD_TARGET
        echo "    Build complete."
    else
        echo "    [ERROR] build_mac.sh not found or not executable."
        echo "            Run: chmod +x build_mac.sh"
        exit 1
    fi

    echo "    .app bundle: dist/$APP_NAME.app"
    if [ "$BUILD_TARGET" = "dmg" ]; then
        DMG_FILE=$(ls -t dist/*.dmg 2>/dev/null | head -1)
        if [ -n "$DMG_FILE" ]; then
            echo "    .dmg:        $DMG_FILE"
        fi
    fi
else
    echo "    Skipping rebuild."
fi

echo ""

# ═══════════════════════════════════════════════════════════════
# Step 3 — Upload to GitHub?
# ═══════════════════════════════════════════════════════════════
read -p "[3/4] Upload to GitHub? [Y/N]: " DO_PUSH

if [[ "$DO_PUSH" =~ ^[Yy] ]]; then
    # --- Commit message ---
    if $VERSION_BUMPED; then
        DEFAULT_MSG="release: v$NEW_VERSION"
    elif $NEW_CHANGES; then
        DEFAULT_MSG="update: sync upstream changes"
    else
        DEFAULT_MSG="update: rebuild macOS package"
    fi

    read -p "    Enter commit message (press Enter for '$DEFAULT_MSG'): " COMMIT_MSG
    COMMIT_MSG="${COMMIT_MSG:-$DEFAULT_MSG}"

    echo "    git add . ..."
    git add .

    echo "    git commit ..."
    if git commit -m "$COMMIT_MSG" 2>/dev/null; then
        echo "    git push ..."
        git push
        echo "    Pushed to GitHub."
    else
        echo "    [WARN] git commit failed (nothing to commit?)"
    fi
else
    echo "    Skipping GitHub upload."
fi

# ═══════════════════════════════════════════════════════════════
# Step 4 — Summary
# ═══════════════════════════════════════════════════════════════
echo ""
echo "============================================"
echo "  Update Complete!"
echo "============================================"
echo ""
if [[ "$DO_BUILD" =~ ^[Yy] ]]; then
    echo "  .app:        dist/$APP_NAME.app"
fi
if $VERSION_BUMPED; then
    echo "  Version:     v$NEW_VERSION"
fi
if $NEW_CHANGES; then
    echo "  Upstream:    new commits integrated"
fi
if [[ "$DO_PUSH" =~ ^[Yy] ]]; then
    echo "  Git:         committed & pushed"
fi
echo ""
