"""File manager: load local files and download from URL / GitHub."""

import os
import re
import hashlib
import tempfile
from pathlib import Path
from urllib.parse import urlparse

import requests
from music21 import converter


def detect_format(path: str) -> str:
    ext = Path(path).suffix.lower()
    format_map = {
        ".musicxml": "musicxml",
        ".xml": "musicxml",
        ".mxl": "musicxml",
        ".midi": "midi",
        ".mid": "midi",
        ".mei": "mei",
        ".abc": "abc",
        ".krn": "humdrum",
    }
    return format_map.get(ext, "musicxml")


def _patch_mei_parsers():
    """Monkey-patch music21's MEI parser to handle malformed elements gracefully.

    music21's MEI parser crashes on certain malformed elements (beams, tuplets,
    ties, etc.) that reference non-existent note IDs. This patch wraps the core
    element-processing loop to skip any element that causes an error, allowing
    the rest of the score to parse correctly.
    """
    try:
        from music21.mei import base as mei_base

        _orig_process = mei_base._processEmbeddedElements

        def safe_process(elements, mapping, callerTag=None, slurBundle=None):
            result = []
            for each_elem in elements:
                tag = each_elem.tag
                if tag not in mapping:
                    continue
                try:
                    converted = mapping[tag](each_elem, slurBundle)
                    if converted is not None:
                        if hasattr(converted, '__iter__') and not isinstance(converted, str):
                            result.extend(converted)
                        else:
                            result.append(converted)
                except Exception:
                    # Skip any element that causes a parser error
                    continue
            return result

        mei_base._processEmbeddedElements = safe_process
    except Exception:
        pass


_patch_mei_parsers()


def load_local_file(path: str):
    """Load a local MusicXML/MIDI/MEI/ABC/KRN file and return a music21 Score."""
    fmt = detect_format(path)
    try:
        return converter.parse(path, format=fmt)
    except IndexError:
        if fmt == 'mei':
            # Still failing after patch — strip beams from XML and retry
            with open(path, 'r', encoding='utf-8') as f:
                cleaned = f.read()
            for tag in ('beam', 'tuplet', 'tupletSpan'):
                cleaned = re.sub(rf'<{tag}\b[^>]*/?>', '', cleaned)
                cleaned = re.sub(rf'<{tag}\b[^>]*>.*?</{tag}>', '', cleaned, flags=re.DOTALL)
            tmp = tempfile.NamedTemporaryFile(mode='w', suffix='.mei',
                                              delete=False, encoding='utf-8')
            try:
                tmp.write(cleaned)
                tmp.close()
                return converter.parse(tmp.name, format='mei')
            finally:
                os.unlink(tmp.name)
        raise
    except Exception:
        return converter.parse(path)


def download_from_url(url: str, temp_dir: str) -> tuple:
    """Download a music file from URL. Returns (file_path, score)."""
    os.makedirs(temp_dir, exist_ok=True)

    response = requests.get(url)
    response.raise_for_status()
    content = response.content

    file_hash = hashlib.md5(content).hexdigest()[:8]

    # Determine extension from URL
    parsed = urlparse(url)
    ext = Path(parsed.path).suffix or ".musicxml"

    filename = f"downloaded_{file_hash}{ext}"
    file_path = os.path.join(temp_dir, filename)

    with open(file_path, "wb") as f:
        f.write(content)

    score = converter.parse(file_path)
    return file_path, score


def download_from_github(raw_url: str, temp_dir: str) -> tuple:
    """Download a music file from a GitHub raw URL. Returns (file_path, score)."""
    return download_from_url(raw_url, temp_dir)


def parse_corpus(name: str):
    """Load a score from music21's corpus by name (e.g. 'bach/bwv66.6').

    Returns (name, score) — name is used as the display path.
    """
    from music21 import corpus

    # Help the user if they accidentally type "music21" or similar as the work name
    if not name or '/' not in name:
        raise ValueError(
            f"Invalid corpus name: '{name}'.\n\n"
            "Please enter a valid music21 corpus work name,\n"
            "e.g. 'bach/bwv66.6' or 'beethoven/opus59no3'.\n\n"
            "Click 'Browse Corpus Reference' for the full list."
        )

    try:
        score = corpus.parse(name)
    except FileNotFoundError as e:
        # Likely corpus data files not accessible (e.g., in a frozen build)
        raise FileNotFoundError(
            f"Corpus work '{name}' not found.\n\n"
            f"The music21 corpus data files may not be installed or accessible.\n"
            f"Detail: {e}"
        ) from e
    except Exception as e:
        raise RuntimeError(
            f"Failed to load corpus work '{name}'.\n\n"
            f"Make sure this work exists in the music21 corpus.\n"
            f"Detail: {e}"
        ) from e

    return name, score


def get_corpus_list():
    """Return a list of corpus work names from music21 and other available sources."""
    items = []
    try:
        from music21 import corpus
        # Dynamic: query all available corpus paths
        if hasattr(corpus, 'getBachChorales'):
            try:
                items.extend(corpus.getBachChorales())
            except Exception:
                pass
        if hasattr(corpus, 'getCorelli'):
            try:
                items.extend(corpus.getCorelli())  # string quartets
            except Exception:
                pass
        # Also try the generic search
        if hasattr(corpus, 'search'):
            try:
                # Search for common types
                for query in ('string quartet', 'piano sonata', 'symphony'):
                    items.extend(corpus.search(query, 'name'))
            except Exception:
                pass
        # Deduplicate while preserving order
        seen = set()
        unique = []
        for i in items:
            if i not in seen:
                seen.add(i)
                unique.append(i)
        items = unique
    except Exception:
        pass

    if not items:
        # Fallback list of popular works
        items = [
            'bach/bwv1.6', 'bach/bwv2.6', 'bach/bwv57.8', 'bach/bwv66.6',
            'bach/bwv104.6', 'bach/bwv248.42', 'bach/bwv254', 'bach/bwv305',
            'beethoven/opus18no1', 'beethoven/opus18no2', 'beethoven/opus18no3',
            'beethoven/opus18no4', 'beethoven/opus18no5', 'beethoven/opus18no6',
            'beethoven/opus59no1', 'beethoven/opus59no2', 'beethoven/opus59no3',
            'beethoven/opus74', 'beethoven/opus95', 'beethoven/opus131',
            'beethoven/opus132', 'beethoven/opus133',
            'corelli/opus3no1', 'corelli/opus3no2',
            'haydn/opus1no1', 'haydn/opus1no2', 'haydn/opus1no3',
            'haydn/opus33no1', 'haydn/opus33no2', 'haydn/opus33no3',
            'haydn/opus64no1', 'haydn/opus64no2', 'haydn/opus64no3',
            'haydn/opus76no1', 'haydn/opus76no2', 'haydn/opus76no3',
            'mozart/k155', 'mozart/k156', 'mozart/k157', 'mozart/k158',
            'mozart/k387', 'mozart/k421', 'mozart/k428', 'mozart/k458',
            'mozart/k464', 'mozart/k465',
            'schubert/D810', 'schubert/D887',
            'schumann/opus41no1', 'schumann/opus41no2',
            'monteverdi/madrigal.1.1', 'monteverdi/madrigal.1.2',
            'monteverdi/madrigal.2.2', 'monteverdi/madrigal.4.1',
            'palestrina/I_105_Gl_Patri', 'palestrina/III_5_Sicut_cervus',
            'palestrina/VI_17_Tu_es_Petrus',
            'essenFolksong/1', 'essenFolksong/2', 'essenFolksong/3',
            'oneMelody/melody1',
        ]
    return items
