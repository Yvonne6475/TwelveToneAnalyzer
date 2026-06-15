"""
Pre-build preparation script — runs BEFORE NSIS packaging.

Optimizations:
1. Removes junk files (__pycache__, *.pyc, *.pyo, .git/)
2. Pre-zips the dist folder into a single archive for NSIS (Release mode)
3. Generates build stats for progress reporting

Usage:
    python build_prep.py           → clean + stats only
    python build_prep.py --zip     → clean + create dist/app.zip
"""

import os
import sys
import shutil
import zipfile
from pathlib import Path
from datetime import datetime

ROOT = Path(__file__).resolve().parent
DIST = ROOT / "dist" / "TwelveToneAnalyzer"
ZIP_OUT = ROOT / "dist" / "app.zip"

# ── Patterns to exclude ───────────────────────────────────────────
EXCLUDE_DIRS = {
    "__pycache__", ".git", ".mypy_cache", ".pytest_cache",
    "build", "dist", ".venv", ".venv_mac",
}
EXCLUDE_EXTS = {".pyc", ".pyo", ".log", ".tmp"}


def clean_dist():
    """Remove junk files from dist/ to reduce NSIS file count."""
    if not DIST.is_dir():
        print(f"[SKIP] dist/ not found at {DIST}")
        return 0

    removed = 0
    for root, dirs, files in os.walk(DIST, topdown=True):
        # Skip excluded dirs
        dirs[:] = [d for d in dirs if d not in EXCLUDE_DIRS]

        for f in files:
            fp = Path(root) / f
            ext = fp.suffix.lower()
            if ext in EXCLUDE_EXTS:
                fp.unlink()
                removed += 1
                continue
            # Remove empty dirs later

    # Remove empty directories
    for root, dirs, files in os.walk(DIST, topdown=False):
        for d in dirs:
            dp = Path(root) / d
            try:
                dp.rmdir()  # only succeeds if empty
                removed += 1
            except OSError:
                pass

    print(f"[CLEAN] Removed {removed} junk files/dirs from dist/")
    return removed


def count_files():
    """Count files and total size in dist/."""
    total = 0
    total_size = 0
    for root, dirs, files in os.walk(DIST, topdown=True):
        dirs[:] = [d for d in dirs if d not in EXCLUDE_DIRS]
        for f in files:
            fp = Path(root) / f
            if fp.suffix.lower() not in EXCLUDE_EXTS:
                total += 1
                total_size += fp.stat().st_size
    return total, total_size


def create_zip():
    """Create a single ZIP archive of dist/ for fast NSIS packaging."""
    if not DIST.is_dir():
        print(f"[ERROR] dist/ not found at {DIST}")
        sys.exit(1)

    print(f"[ZIP] Creating {ZIP_OUT} ...")
    start = datetime.now()

    file_count = 0
    # Use STORE (no compression) — NSIS lzma will compress the whole bundle.
    # DEFLATE pre-compression blocks lzma from achieving good ratios.
    with zipfile.ZipFile(ZIP_OUT, "w", zipfile.ZIP_STORED) as zf:
        for root, dirs, files in os.walk(DIST, topdown=True):
            dirs[:] = [d for d in dirs if d not in EXCLUDE_DIRS]
            for f in files:
                fp = Path(root) / f
                if fp.suffix.lower() in EXCLUDE_EXTS:
                    continue
                arcname = str(fp.relative_to(DIST))
                zf.write(fp, arcname)
                file_count += 1
                if file_count % 500 == 0:
                    print(f"  ... {file_count} files packed")

    elapsed = (datetime.now() - start).total_seconds()
    zip_mb = ZIP_OUT.stat().st_size / (1024 * 1024)
    print(f"[ZIP] Done: {file_count} files → {zip_mb:.1f} MB in {elapsed:.1f}s")


def main():
    import argparse
    p = argparse.ArgumentParser(description="Pre-build cleanup and zip")
    p.add_argument("--zip", action="store_true", help="Create dist/app.zip")
    args = p.parse_args()

    clean_dist()
    file_count, total_size = count_files()
    size_mb = total_size / (1024 * 1024)
    print(f"[STATS] {file_count} files, {size_mb:.1f} MB")

    if file_count > 8000:
        print("[WARN] File count > 8000 — NSIS will be slow. "
              "Run with --zip for fast packaging.")

    if args.zip:
        create_zip()
        zip_mb = ZIP_OUT.stat().st_size / (1024 * 1024)
        ratio = (1 - zip_mb / max(size_mb, 1)) * 100
        print(f"[STATS] ZIP ratio: {ratio:.1f}% smaller, "
              f"NSIS will process 1 file instead of {file_count}")


if __name__ == "__main__":
    main()
