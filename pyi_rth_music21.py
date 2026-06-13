"""PyInstaller runtime hook: fix music21 path resolution in frozen bundles.

music21's `common.pathTools.getSourceFilePath()` uses `inspect.getfile()` +
`os.listdir()` to locate its data directory.  Inside a PyInstaller bundle,
compiled modules live inside PYZ archives, so `inspect.getfile()` returns
a non-existent virtual path.  This causes `FileNotFoundError` when any
music21 feature tries to access corpus / metadata / notation data.

This hook patches `getSourceFilePath()` to resolve against the *real*
filesystem copy of `music21/` that `collect_all('music21')` extracts
into the COLLECT directory (accessible via `sys._MEIPASS`).

Place this file alongside the .spec and register it as:
    runtime_hooks=['pyi_rth_music21.py', ...]
"""

import sys
import os
import pathlib


def _patch_music21_source_path():
    """Redirect music21's source-file detection to sys._MEIPASS."""
    if not getattr(sys, 'frozen', False):
        return  # not in a PyInstaller bundle — nothing to do

    bundle_dir = sys._MEIPASS
    music21_dir = os.path.join(bundle_dir, 'music21')

    # Sanity check: music21 data must have been collected
    stream_dir = os.path.join(music21_dir, 'stream')
    if not os.path.isdir(stream_dir):
        return  # music21 not bundled — skip

    try:
        from music21.common import pathTools

        # Save original for potential fallback
        _original_get_source = pathTools.getSourceFilePath

        def _bundled_getSourceFilePath():
            return pathlib.Path(music21_dir)

        pathTools.getSourceFilePath = _bundled_getSourceFilePath
    except Exception:
        pass


_patch_music21_source_path()
