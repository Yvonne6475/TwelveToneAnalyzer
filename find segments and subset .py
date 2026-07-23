
"""
find segments and subset .py

全声部、跨小节——自动寻找所有音级集合及其子集
==========================================================================

解析 MusicXML/MEI 总谱，提取所有声部的所有音符，在全局时间轴上：
  1. 滑动窗口检测所有完整的十二音序列行
  2. 按小节窗口分段，计算每段的 Forte 分类
  3. 找出每段内所有子集及其集合类
  4. 跨声部同时发声集合对比

Usage:
  .venv_mac/bin/python3 "find segments and subset .py" [score.musicxml]

如果没有传入乐谱文件，会自动从 GitHub 下载 Luo String Quartet No.2 作为示例。
"""

from __future__ import annotations

import os
import sys
import hashlib
import logging
import tempfile
from dataclasses import dataclass
from typing import Optional

import numpy as np
from music21 import converter, stream, note, chord, instrument, clef, meter, key


logging.basicConfig(level=logging.INFO, format="[%(levelname)s] %(message)s")
logger = logging.getLogger(__name__)

NOTE_NAMES = ["C", "C#", "D", "D#", "E", "F",
              "F#", "G", "G#", "A", "A#", "B"]


# ──────────────────────────────────────────────────────────────────────
# Data structures
# ──────────────────────────────────────────────────────────────────────

@dataclass
class NoteEvent:
    """A single note (or chord constituent) with global time coordinates."""
    note_id: int
    part_name: str
    part_index: int
    pitch_name: str
    pitch_class: int
    midi: int
    start_global: float
    end_global: float
    measure: int
    quarter_length: float


@dataclass
class RowCandidate:
    """A complete 12-tone row found via sliding window."""
    index: int
    start_note_id: int
    end_note_id: int
    pitch_classes: list[int]
    measure_range: tuple
    parts_involved: set[str]
    note_count: int


@dataclass
class AnalysisSegment:
    """A segment of the score analyzed for set classes."""
    label: str
    measures: tuple
    parts_involved: set[str]
    pitch_classes: list[int]
    pc_set: list[int]          # sorted unique pitch classes
    cardinality: int
    prime_form: str
    forte_class: str
    interval_vector: list[int]
    per_part_pcs: dict = None
    note_count: int = 0
    part_count: int = 0
    pitch_range: int = 0
    avg_ql: float = 0.0
    subsets: list[dict] = None


# ──────────────────────────────────────────────────────────────────────
# Core extraction
# ──────────────────────────────────────────────────────────────────────

def extract_all_notes(score_path: str) -> tuple:
    """Parse a score file and extract ALL notes from ALL parts.

    Returns (score, events, part_names) where events is a flat list of
    NoteEvent sorted by global time, across all parts.
    """
    score = converter.parse(score_path)

    # Unwrap Opus if needed
    from music21.stream import Opus as M21Opus, Score as M21Score
    if isinstance(score, M21Opus):
        merged = M21Score()
        for child in score.scores:
            if isinstance(child, M21Score):
                for p in child.parts:
                    merged.insert(0, p)
        score = merged

    part_names = []
    events: list[NoteEvent] = []
    note_id = 0

    for part_idx, part in enumerate(score.parts):
        pname = part.partName or f"Part {part_idx + 1}"
        part_names.append(pname)

        for n in part.flatten().notes:
            if isinstance(n, note.Note):
                note_id += 1
                events.append(NoteEvent(
                    note_id=note_id,
                    part_name=pname,
                    part_index=part_idx,
                    pitch_name=n.nameWithOctave,
                    pitch_class=n.pitch.pitchClass,
                    midi=n.pitch.midi,
                    start_global=n.offset,
                    end_global=n.offset + n.quarterLength,
                    measure=n.measureNumber or 0,
                    quarter_length=n.quarterLength,
                ))
            elif isinstance(n, chord.Chord):
                for sub in n.pitches:
                    note_id += 1
                    events.append(NoteEvent(
                        note_id=note_id,
                        part_name=pname,
                        part_index=part_idx,
                        pitch_name=sub.nameWithOctave,
                        pitch_class=sub.pitchClass,
                        midi=sub.midi,
                        start_global=n.offset,
                        end_global=n.offset + n.quarterLength,
                        measure=n.measureNumber or 0,
                        quarter_length=n.quarterLength,
                    ))

    events.sort(key=lambda e: (e.start_global, e.part_index, e.midi))
    logger.info(f"Extracted {len(events)} note events from {len(part_names)} parts")
    for pn in part_names:
        cnt = sum(1 for e in events if e.part_name == pn)
        logger.info(f"  {pn}: {cnt} notes")

    return score, events, part_names


# ──────────────────────────────────────────────────────────────────────
# 12-tone row detection via sliding window
# ──────────────────────────────────────────────────────────────────────

def find_all_rows(events: list[NoteEvent], min_parts: int = 1) -> list[RowCandidate]:
    """Slide a window over all notes (sorted by time) to find complete 12-tone rows.

    A "complete 12-tone row" = 12 consecutive pitch-class events that
    contain every pitch class 0–11 exactly once.

    Parameters
    ----------
    events : list[NoteEvent] sorted by global time
    min_parts : int
        Minimum number of distinct parts the row must span.
        Default 1 (any single part or cross-part).

    Returns list of RowCandidate.
    """
    if len(events) < 12:
        return []

    found: list[RowCandidate] = []
    seen_sets: set = set()  # dedup by frozenset of PCs

    for i in range(len(events) - 11):
        window = events[i:i + 12]
        pcs = [e.pitch_class for e in window]
        pc_set = set(pcs)

        if len(pc_set) == 12:
            # Check min_parts constraint
            parts = set(e.part_name for e in window)
            if len(parts) < min_parts:
                continue

            # Dedup: same PC set at different positions may be same row
            key = frozenset(pcs)
            if key in seen_sets:
                continue
            seen_sets.add(key)

            meas = [e.measure for e in window if e.measure > 0]
            meas_range = (min(meas), max(meas)) if meas else (0, 0)

            found.append(RowCandidate(
                index=len(found) + 1,
                start_note_id=window[0].note_id,
                end_note_id=window[-1].note_id,
                pitch_classes=pcs,
                measure_range=meas_range,
                parts_involved=parts,
                note_count=12,
            ))

    logger.info(f"Found {len(found)} complete 12-tone row(s) via sliding window")
    return found


# ──────────────────────────────────────────────────────────────────────
# Segment analysis
# ──────────────────────────────────────────────────────────────────────

def analyze_by_measure_windows(
    events: list[NoteEvent],
    window_size: int = 4,
    stride: int = 2,
) -> list[AnalysisSegment]:
    """Divide the score into overlapping measure windows and analyze each.

    For each window, collects ALL pitch classes from ALL parts, deduplicates,
    and computes Forte classification.

    Parameters
    ----------
    events : list[NoteEvent]
    window_size : int — number of measures per window (default 4)
    stride : int — how many measures to slide each step (default 2, partial overlap)

    Returns list of AnalysisSegment.
    """
    if not events:
        return []

    all_measures = sorted(set(e.measure for e in events if e.measure > 0))
    if not all_measures:
        return []

    max_m = max(all_measures)
    segments: list[AnalysisSegment] = []
    seg_idx = 1

    start = min(all_measures)
    while start <= max_m:
        end = min(start + window_size - 1, max_m)

        # Collect notes in this measure range
        window_notes = [
            e for e in events
            if start <= e.measure <= end
        ]

        if window_notes:
            pcs = sorted(set(e.pitch_class for e in window_notes))
            parts = set(e.part_name for e in window_notes)
            note_count = len(window_notes)
            active_parts = len(parts)
            midis = [e.midi for e in window_notes]
            pitch_range = max(midis) - min(midis) if midis else 0
            avg_ql = sum(e.quarter_length for e in window_notes) / note_count if note_count else 0

            # Collect per-part pitch classes
            per_part = {}
            for e in window_notes:
                per_part.setdefault(e.part_name, set()).add(e.pitch_class)
            per_part_pcs = {pn: sorted(pps) for pn, pps in per_part.items()}

            c = chord.Chord(pcs)
            seg = AnalysisSegment(
                label=f"m.{start}–{end}",
                measures=(start, end),
                parts_involved=parts,
                pitch_classes=[e.pitch_class for e in window_notes],
                pc_set=pcs,
                cardinality=len(pcs),
                prime_form=c.primeFormString,
                forte_class=c.forteClass,
                interval_vector=list(c.intervalVector),
                per_part_pcs=per_part_pcs,
                note_count=note_count,
                part_count=active_parts,
                pitch_range=pitch_range,
                avg_ql=avg_ql,
            )
            # Subsets are computed lazily in print_subset_table
            segments.append(seg)

        start += stride
        seg_idx += 1

    logger.info(f"Generated {len(segments)} analysis segments "
                f"(window={window_size}, stride={stride})")
    return segments


def compute_subsets(pcs: list[int]) -> list[dict]:
    """Given a pitch-class set, compute all non-empty proper subsets
    with their Forte classifications, grouped by cardinality.

    Returns list of dicts: {pcs, prime_form, forte_class, cardinality}.
    """
    from itertools import combinations

    results = []
    seen_forte: set = set()

    pcs_sorted = sorted(set(pcs))
    # Cap at cardinality 6 to keep computation reasonable
    max_k = min(len(pcs_sorted) - 1, 6)
    for k in range(1, max_k + 1):
        for combo in combinations(pcs_sorted, k):
            c = chord.Chord(list(combo))
            fc = c.forteClass
            # Dedup by Forte class
            key = (fc, tuple(sorted(combo)))
            if key in seen_forte:
                continue
            seen_forte.add(key)
            results.append({
                "pcs": sorted(combo),
                "prime_form": c.primeFormString,
                "forte_class": fc,
                "cardinality": k,
            })

    # Sort by cardinality, then by Forte class
    results.sort(key=lambda r: (r["cardinality"], r["forte_class"]))
    return results


# ──────────────────────────────────────────────────────────────────────
# Cross-voice harmonic analysis
# ──────────────────────────────────────────────────────────────────────

def analyze_cross_voice_harmony(events: list[NoteEvent]) -> list[dict]:
    """Find simultaneous pitch collections across all parts.

    A "simultaneous" set = notes whose start_global times are within
    0.25 quarter beats of each other, across different parts.

    Returns list of dicts with time, parts, PCs, and Forte class.
    """
    if not events:
        return []

    results: list[dict] = []
    i = 0
    eps = 0.25

    while i < len(events):
        t = events[i].start_global
        # Collect all notes at approximately this time
        group = []
        j = i
        while j < len(events) and events[j].start_global - t <= eps:
            group.append(events[j])
            j += 1

        # Only keep groups with >= 2 parts
        parts = set(e.part_name for e in group)
        if len(parts) >= 2:
            pcs = sorted(set(e.pitch_class for e in group))
            meas = [e.measure for e in group if e.measure > 0]
            c = chord.Chord(pcs)
            results.append({
                "time": float(round(t, 2)),
                "measure": max(set(meas), key=meas.count) if meas else 0,
                "parts": sorted(parts),
                "pc_count": len(pcs),
                "pcs": pcs,
                "prime_form": c.primeFormString,
                "forte_class": c.forteClass,
                "interval_vector": list(c.intervalVector),
            })

        i = j

    # Sort by measure then time
    results.sort(key=lambda r: (r["measure"], r["time"]))

    # Dedup: keep first occurrence of each Forte class
    seen_forte = set()
    deduped = []
    for r in results:
        if r["forte_class"] not in seen_forte:
            seen_forte.add(r["forte_class"])
            deduped.append(r)

    logger.info(f"Found {len(deduped)} unique cross-voice harmonic sets")
    return deduped
# ──────────────────────────────────────────────────────────────────────

def generate_forms(pc_list: list[int]) -> dict:
    """Generate P, R, I, RI forms of a 12-tone row."""
    pivot = pc_list[0]
    p_row = list(pc_list)
    r_row = list(reversed(pc_list))
    i_row = [(2 * pivot - p) % 12 for p in p_row]
    ri_row = [(2 * pivot - p) % 12 for p in r_row]
    return {
        f"P{p_row[0]}": p_row,
        f"R{r_row[0]}": r_row,
        f"I{i_row[0]}": i_row,
        f"RI{ri_row[0]}": ri_row,
    }


# ──────────────────────────────────────────────────────────────────────
# Display functions
# ──────────────────────────────────────────────────────────────────────

def print_score_overview(score, events, part_names):
    """Print basic score metadata."""
    all_meas = sorted(set(e.measure for e in events if e.measure > 0))
    total_notes = len(events)
    total_parts = len(part_names)
    meas_range = f"{min(all_meas)}–{max(all_meas)}" if all_meas else "N/A"

    print()
    print("  Score Overview")
    print("  " + "-" * 50)
    print(f"  Parts:       {total_parts}")
    for pn in part_names:
        cnt = sum(1 for e in events if e.part_name == pn)
        print(f"    {pn}: {cnt} notes")
    print(f"  Total notes: {total_notes}")
    print(f"  Measure range: {meas_range}")
    print()


def print_row_table(rows: list[RowCandidate]):
    """Print found 12-tone rows."""
    if not rows:
        print("  (no complete 12-tone rows found)")
        return

    print()
    print(f"  Found {len(rows)} complete 12-tone row(s):")
    print()
    header = (
        f"  {'#':>3}  {'Bars':<10} {'Parts':<30} {'Pitch Classes (PC)'}"
    )
    print(header)
    print("  " + "-" * (len(header) + 10))
    for r in rows:
        parts_str = ", ".join(sorted(r.parts_involved))
        bar_str = f"{r.measure_range[0]}–{r.measure_range[1]}"
        pc_str = ",".join(str(p) for p in r.pitch_classes)
        pc_names = ",".join(NOTE_NAMES[p] for p in r.pitch_classes)
        print(f"  {r.index:>3}  {bar_str:<10} {parts_str:<30} {pc_str}")
        print(f"      {'':10} {'':30} {pc_names}")
    print()


def print_segment_table(segments: list[AnalysisSegment], max_rows: int = 60):
    """Print segment analysis table."""
    if not segments:
        print("  (no segments)")
        return

    print()
    header = (
        f"  {'Segment':<14} {'Size':>4}  {'PCs':<20} "
        f"{'Notes':>5} {'Parts':>5} {'Range':>5} {'AvgQL':>5} {'Parts'}"
    )
    print(header)
    print("  " + "-" * (len(header) + 20))

    for seg in segments[:max_rows]:
        pc_str = ",".join(str(p) for p in seg.pc_set)
        part_str = ", ".join(sorted(seg.parts_involved))
        print(
            f"  {seg.label:<14} {seg.cardinality:>4}  {pc_str:<20} "
            f"{seg.note_count:>5} {seg.part_count:>5} {seg.pitch_range:>5} {seg.avg_ql:>5.1f} {part_str}"
        )
        # Per-part Forte analysis
        if seg.per_part_pcs and len(seg.per_part_pcs) > 1:
            for pn in sorted(seg.per_part_pcs.keys()):
                pcs = seg.per_part_pcs[pn]
                c = chord.Chord(pcs)
                pp_str = ",".join(str(p) for p in pcs)
                print(f"    {pn:<16} [{pp_str}]  {c.primeFormString:<10} {c.forteClass:<8}")
        print(f"  ... and {len(segments) - max_rows} more segments")
    print()


def print_subset_table(segments: list[AnalysisSegment], max_segs: int = 8):
    """Print subset analysis for segments with 4+ pitch classes."""
    # Sort by cardinality desc, pick most interesting
    candidates = [s for s in segments if s.cardinality >= 4]
    candidates.sort(key=lambda s: s.cardinality, reverse=True)

    for seg in candidates[:max_segs]:
        # Compute subsets lazily (only for displayed segments)
        # Skip full-chromatic sets (all 12 PCs) — subsets are trivial
        if seg.cardinality >= 10:
            continue
        subsets = compute_subsets(seg.pc_set)
        # Only show segments with interesting subset diversity
        if len(subsets) < 5:
            continue
        print(f"  Subsets of {seg.label}  (PCs={seg.pc_set}, Forte={seg.forte_class})")
        print("  " + "-" * 60)
        sub_header = f"    {'Card':>4}  {'PCs':<18} {'Prime':<12} {'Forte':<10}"
        print(sub_header)
        print("    " + "-" * (len(sub_header) - 2))
        for s in subsets[:20]:
            pc_str = ",".join(str(p) for p in s["pcs"])
            print(f"    {s['cardinality']:>4}  {pc_str:<18} "
                  f"{s['prime_form']:<12} {s['forte_class']:<10}")
        if len(subsets) > 20:
            print(f"    ... and {len(subsets) - 20} more subsets")
        print()


def print_harmony_table(harmonies: list[dict]):
    """Print cross-voice harmonic analysis."""
    if not harmonies:
        print("  (no multi-part simultaneous sets found)")
        return

    print()
    header = (
        f"  {'Time':>7}  {'Bar':>4}  {'Parts':<35} {'Count':>3}  "
        f"{'PC Set':<18} {'Prime':<12} {'Forte':<10}"
    )
    print(header)
    print("  " + "-" * (len(header) + 10))
    for h in harmonies:
        parts_str = ", ".join(h["parts"][:4])
        if len(h["parts"]) > 4:
            parts_str += f" (+{len(h['parts'])-4})"
        pc_str = ",".join(str(p) for p in h["pcs"])
        print(
            f"  {h['time']:>7.2f}  {h['measure']:>4}  {parts_str:<35} "
            f"{h['pc_count']:>3}  {pc_str:<18} "
            f"{h['prime_form']:<12} {h['forte_class']:<10}"
        )
    print()


# ──────────────────────────────────────────────────────────────────────
# Full analysis pipeline
# ──────────────────────────────────────────────────────────────────────

def analyze_score(score_path: str, window_size: int = 4, stride: int = 2):
    """Run the complete analysis pipeline on a score file.

    Parameters
    ----------
    score_path : str
        Path to MusicXML, MEI, or MIDI file.
    window_size : int
        Measures per analysis segment window (default 4).
    stride : int
        Measure stride between windows (default 2, creates overlapping windows).
    """
    print()
    print("╔══════════════════════════════════════════════════════════════╗")
    print("║                                                              ║")
    print("║   TwelveToneAnalyzer — Find Segments & Subsets               ║")
    print("║   Full-score, all-voice set theory analysis                  ║")
    print("║                                                              ║")
    print("╚══════════════════════════════════════════════════════════════╝")
    print()
    print(f"  Score: {os.path.basename(score_path)}")

    # Step 1: Extract all notes
    print()
    print("─" * 60)
    print("  Step 1: Extract ALL notes from ALL parts")
    print("─" * 60)
    score, events, part_names = extract_all_notes(score_path)
    print_score_overview(score, events, part_names)

    # Step 2: Sliding window 12-tone row detection
    print("─" * 60)
    print("  Step 2: Sliding-window 12-tone row detection")
    print("─" * 60)
    rows = find_all_rows(events)
    print_row_table(rows)

    # Step 3: Measure-window segmentation
    print("─" * 60)
    print(f"  Step 3: Measure-window segmentation "
          f"(window={window_size} bars, stride={stride})")
    print("─" * 60)
    segments = analyze_by_measure_windows(events, window_size=window_size, stride=stride)
    print_segment_table(segments)

    # Step 4: Subset analysis
    print("─" * 60)
    print("  Step 4: Subset analysis (within each segment)")
    print("─" * 60)
    print_subset_table(segments)

    # Step 5: Cross-voice harmonic analysis
    print("─" * 60)
    print("  Step 5: Cross-voice harmonic analysis")
    print("─" * 60)
    harmonies = analyze_cross_voice_harmony(events)
    print_harmony_table(harmonies)

    # Step 6: Per-part analysis
    print("─" * 60)
    print("  Step 6: Per-part measure window analysis")
    print("─" * 60)
    for pname in part_names:
        p_events = [e for e in events if e.part_name == pname]
        p_segs = analyze_by_measure_windows(p_events, window_size=window_size, stride=stride)
        print(f"  ── {pname} ({len(p_events)} notes) ──")
        # Only show segments with 4+ unique pitch classes
        rich_segs = [s for s in p_segs if s.cardinality >= 4]
        if rich_segs:
            print_segment_table(rich_segs[:20])
        else:
            # Show all if none are 4+
            print(f"    (no segments with 4+ unique pitch classes)")
            if p_segs:
                print_segment_table(p_segs[:10])
        print()

    # Step 7: SSM-based structural analysis
    print("─" * 60)
    print("  Step 7: SSM-based structural analysis")
    print("─" * 60)
    if len(segments) >= 5:
        row_pcs = rows[0].pitch_classes if rows else None
        feat_mat = build_feature_matrix(segments, row_pcs)
        ssm = compute_ssm(feat_mat)
        boundaries = detect_boundaries(ssm, kernel_size=3)
        labels = label_segments(boundaries, len(segments))
        refined_labels = refine_labels(labels, feat_mat, similarity_threshold=0.95)
        form_type = determine_form_type(refined_labels)
        print(f"  Form analysis:          {form_type}")
        # Twelve-tone form analysis
        print("─" * 60)
        print("  Row-Form Analysis (per section)")
        print("─" * 60)
        print_form_analysis(segments, refined_labels, events, row_pcs)
        print_structure_summary(segments, boundaries, refined_labels)
    print()

    # Summary
    print("=" * 70)
    print("  Summary")
    print("=" * 70)
    print(f"  Total notes extracted:  {len(events)}")
    print(f"  Total parts:            {len(part_names)}")
    print(f"  12-tone rows found:     {len(rows)}")
    print(f"  Measure segments:       {len(segments)}")
    print(f"  Cross-voice harmonies:  {len(harmonies)}")
    if len(segments) >= 5:
        print(f"  Structural boundaries:  {len(boundaries)}")
    print()

    return {
        "score": score,
        "events": events,
        "part_names": part_names,
        "rows": rows,
        "segments": segments,
        "harmonies": harmonies,
    }


# ──────────────────────────────────────────────────────────────────────
# Main / CLI entry point
# ──────────────────────────────────────────────────────────────────────

def download_corpus_score() -> str:
    """Download the Luo String Quartet No. 2 as a demo score.

    Returns path to the downloaded file.
    """
    # Try MusicXML first (MEI has parsing bug in music21 8.3)
    urls = [
        ("MusicXML",
         "https://raw.githubusercontent.com/Yvonne6475/"
         "My-music-Corpus-Library/refs/heads/main/"
         "Luo's_String_Quartet_No.2_full_score.musicxml"),
        ("MEI",
         "https://raw.githubusercontent.com/Yvonne6475/"
         "My-music-Corpus-Library/refs/heads/main/"
         "Luo's_String_Quartet_No.2_full_score.mei"),
    ]

    import urllib.request
    import ssl

    ssl_ctx = ssl.create_default_context()
    ssl_ctx.check_hostname = False
    ssl_ctx.verify_mode = ssl.CERT_NONE

    temp_dir = tempfile.gettempdir()

    for fmt, url in urls:
        ext = ".musicxml" if fmt == "MusicXML" else ".mei"
        print(f"  Downloading {fmt}...")
        try:
            with urllib.request.urlopen(url, timeout=60, context=ssl_ctx) as resp:
                data = resp.read()
            fhash = hashlib.md5(data).hexdigest()[:8]
            path = os.path.join(temp_dir, f"Luo_Quartet_{fhash}{ext}")
            with open(path, "wb") as f:
                f.write(data)
            print(f"  Downloaded {fmt} ({len(data):,} bytes)")
            return path
        except Exception as e:
            print(f"  ⚠ {fmt} failed: {e}")

    print("  ❌ Could not download demo score.")
    sys.exit(1)


def main():
    """Main entry point."""
    # Get score path from CLI or download demo
    if len(sys.argv) > 1:
        score_path = sys.argv[1]
        if not os.path.exists(score_path):
            print(f"File not found: {score_path}")
            sys.exit(1)
    else:
        print("No score provided — downloading Luo String Quartet No. 2 as example...")
        score_path = download_corpus_score()

    # Optional: window size and stride from CLI
    window_size = int(sys.argv[2]) if len(sys.argv) > 2 else 4
    stride = int(sys.argv[3]) if len(sys.argv) > 3 else 2

    analyze_score(score_path, window_size=window_size, stride=stride)



# ──────────────────────────────────────────────────────────────────────
# Self-Similarity Matrix + boundary detection (formal analysis)
# ──────────────────────────────────────────────────────────────────────

def compute_sequence_distribution(seg: AnalysisSegment, row_pcs: list[int]) -> list[int]:
    """Count how many pitch classes in the segment belong to each row form (P/I/R/RI).

    Returns [count_P, count_I, count_R, count_RI] distribution.
    """
    if not row_pcs or len(row_pcs) != 12:
        return [0, 0, 0, 0]

    pivot = row_pcs[0]
    p_set = set(row_pcs)
    i_set = set((2 * pivot - p) % 12 for p in row_pcs)
    r_set = set(reversed(row_pcs))
    ri_set = set((2 * pivot - p) % 12 for p in reversed(row_pcs))

    seg_pcs_set = set(seg.pc_set)
    return [
        len(seg_pcs_set & p_set),
        len(seg_pcs_set & i_set),
        len(seg_pcs_set & r_set),
        len(seg_pcs_set & ri_set),
    ]


def build_feature_matrix(segments: list[AnalysisSegment], row_pcs: list[int] | None = None) -> np.ndarray:
    """Build a feature matrix from analysis segments for SSM computation.

    Each row = one window. Features:
      - cardinality, note_count, part_count, pitch_range, avg_ql
      - interval_vector (6 values)
      - sequence form distribution: P/I/R/RI counts (4 values, if row_pcs given)
    """
    if not segments:
        return np.array([])

    n = len(segments)
    feat_list = []
    for seg in segments:
        vec = [
            seg.cardinality,
            seg.note_count,
            seg.part_count,
            seg.pitch_range,
            seg.avg_ql,
        ]
        vec.extend(seg.interval_vector)
        if row_pcs:
            vec.extend(compute_sequence_distribution(seg, row_pcs))
        feat_list.append(vec)

    mat = np.array(feat_list, dtype=float)
    col_min = mat.min(axis=0)
    col_max = mat.max(axis=0)
    col_range = col_max - col_min
    col_range[col_range == 0] = 1
    mat_norm = (mat - col_min) / col_range
    return mat_norm


def compute_ssm(feature_matrix: np.ndarray) -> np.ndarray:
    """Compute Self-Similarity Matrix via cosine similarity.

    Returns N×N matrix where entry [i,j] = similarity between window i and j.
    """
    n = feature_matrix.shape[0]
    norms = np.linalg.norm(feature_matrix, axis=1, keepdims=True)
    norms[norms == 0] = 1
    ssm = (feature_matrix @ feature_matrix.T) / (norms @ norms.T)
    # Clamp to [0, 1]
    ssm = np.clip(ssm, 0, 1)
    return ssm


def detect_boundaries(ssm: np.ndarray, kernel_size: int = 5) -> list[int]:
    """Detect structural boundaries via Foote novelty kernel.

    Parameters
    ----------
    ssm : np.ndarray
        N×N self-similarity matrix.
    kernel_size : int
        Size of the checkerboard kernel (odd). Default 5.

    Returns list of boundary indices (window indices where novelty peaks).
    """
    n = ssm.shape[0]
    if n < kernel_size + 2:
        return []

    # Checkerboard kernel
    k2 = kernel_size // 2
    kernel = np.zeros((kernel_size, kernel_size))
    # Upper-left and lower-right quadrants = +1 (same blocks)
    # Upper-right and lower-left quadrants = -1 (transition blocks)
    for i in range(kernel_size):
        for j in range(kernel_size):
            if (i < k2 and j < k2) or (i >= k2 and j >= k2):
                kernel[i, j] = 1.0 / (k2 * k2)
            else:
                kernel[i, j] = -1.0 / (k2 * (kernel_size - k2))

    # Convolve: novelty curve
    novelty = np.zeros(n)
    for i in range(k2, n - k2):
        patch = ssm[i - k2:i + k2 + 1, i - k2:i + k2 + 1]
        novelty[i] = np.sum(patch * kernel)

    # Zero out edges
    novelty[:k2] = 0
    novelty[-k2:] = 0

    # Find peaks above mean + 1 std
    threshold = novelty.mean() + 0.5 * novelty.std()
    boundaries = []
    for i in range(1, n - 1):
        if novelty[i] > threshold and novelty[i] > novelty[i - 1] and novelty[i] > novelty[i + 1]:
            boundaries.append(i)

    return boundaries


def label_segments(boundaries: list[int], n_windows: int) -> list[str]:
    """Assign section labels (A, B, C...) based on detected boundaries.

    Simulates simple form analysis: segments between boundaries get
    ascending labels. Repeated sections are not yet identified.
    """
    if not boundaries or n_windows == 0:
        return ["A"] * max(n_windows, 1)

    # Split points including start and end
    splits = [0] + sorted(boundaries) + [n_windows]
    labels = []
    # Deduplicate adjacent
    clean = [splits[0]]
    for s in splits[1:]:
        if s != clean[-1]:
            clean.append(s)

    section_names = ["A", "B", "C", "D", "E", "F", "G"]
    for i in range(len(clean) - 1):
        count = clean[i + 1] - clean[i]
        label = section_names[i % len(section_names)]
        labels.extend([label] * count)

    # Trim to exact length
    return labels[:n_windows]


def print_structure_summary(
    segments: list[AnalysisSegment],
    boundaries: list[int],
    labels: list[str],
    max_rows: int = 60,
):
    """Print structural analysis summary with section labels."""
    if not segments:
        return

    print()
    print("  Structural Analysis (SSM-based)")
    print("  " + "-" * 60)
    print(f"  Windows:          {len(segments)}")
    print(f"  Detected boundaries: {len(boundaries)} at windows: {boundaries}")
    # Infer form_type from labels if not passed
    form_type = determine_form_type(labels) if hasattr(determine_form_type, '__call__') else ""
    print()
    # Add sequence distribution note
    seq_labels = sorted(set(labels), key=lambda x: labels.index(x))
    arrow = "\u2192"
    print(f"  Section labeling:  {arrow.join(seq_labels)}")
    print(f"  Form type:         {form_type}")
    print()

    header = (
        f"  {'Seg#':>4}  {'Window':<10} {'Label':>4}  "
        f"{'Size':>3} {'Notes':>5} {'Parts':>4} {'Range':>4}  {'PCs'}"
    )
    print(header)
    print("  " + "-" * (len(header) + 10))

    for i, seg in enumerate(segments[:max_rows]):
        pc_str = ",".join(str(p) for p in seg.pc_set)
        label = labels[i] if i < len(labels) else "?"
        print(
            f"  {i + 1:>4}  {seg.label:<10} {label:>4}  "
            f"{seg.cardinality:>3} {seg.note_count:>5} {seg.part_count:>4} "
            f"{seg.pitch_range:>4}  {pc_str}"
        )

    if len(segments) > max_rows:
        print(f"  ... and {len(segments) - max_rows} more windows")
    print()

    # Print section summary
    print("  Section Summary")
    print("  " + "-" * 40)
    unique_labels = sorted(set(labels), key=lambda x: labels.index(x))
    for lbl in unique_labels:
        indices = [i for i, l in enumerate(labels) if l == lbl]
        wins = [segments[i] for i in indices]
        meas = [w.measures for w in wins]
        start_m = min(m[0] for m in meas)
        end_m = max(m[1] for m in meas)
        pcs_all = set()
        for w in wins:
            pcs_all.update(w.pc_set)
        print(f"    {lbl}: windows {indices[0] + 1}–{indices[-1] + 1}  "
              f"(m.{start_m}–{end_m})  {len(pcs_all)} PCs")
    print()


def refine_labels(
    labels: list[str],
    feat_mat: np.ndarray,
    similarity_threshold: float = 0.85,
) -> list[str]:
    """Refine section labels by detecting similar sections.

    Compares each non-A section's mean feature vector with A's mean
    using Euclidean distance on texture features (first 5 columns).
    Only the LAST section is checked — if it's close to A, it's a reprise.
    """
    if len(labels) < 3 or feat_mat.shape[0] < 3:
        return labels

    unique_labels = sorted(set(labels), key=lambda x: labels.index(x))
    if "A" not in unique_labels:
        return labels

    n_texture = min(5, feat_mat.shape[1])
    tex_mat = feat_mat[:, :n_texture]

    a_indices = [i for i, l in enumerate(labels) if l == "A"]
    a_mean = tex_mat[a_indices].mean(axis=0)

    refined = list(labels)
    # Only check the LAST unique label for possible reprise
    last_lbl = [l for l in unique_labels if l != "A"][-1] if len([l for l in unique_labels if l != "A"]) > 0 else None
    if last_lbl:
        idxs = [i for i, l in enumerate(labels) if l == last_lbl]
        mean_vec = tex_mat[idxs].mean(axis=0)
        dist = float(np.linalg.norm(a_mean - mean_vec))
        max_dist = np.sqrt(float(n_texture))
        similarity = 1.0 - (dist / max_dist)
        if similarity > similarity_threshold:
            for i in idxs:
                refined[i] = "A'"

    return refined


def determine_form_type(labels: list[str]) -> str:
    """Determine the overall form type from the section label sequence.

    Detects patterns: A-B (binary), A-B-A (ternary), A-B-A-C-A (rondo),
    A-B-C-D (block), A (continuous), etc.
    """
    # Get unique labels in order of first appearance
    seen = []
    for l in labels:
        if l not in seen:
            seen.append(l)

    seq_str = "–".join(seen)
    n_distinct = len(seen)
    n_total = len(set(labels))

    if n_distinct == 1:
        return "Continuous (through-composed)"
    if n_distinct == 2:
        if "A'" in labels:
            return "Binary with reprise (A–B–A')"
        return "Binary (A–B)"
    if n_distinct == 3:
        if labels[-1] == "A" or labels[-1] == "A'":
            return "Ternary (A–B–A')"
        if "A'" in labels:
            return "Ternary with varied reprise (A–B–A')"
        return "Three-part sectional (A–B–C)"
    if n_distinct >= 4:
        if "A" in seen[::2]:  # A alternates
            return "Rondo or refrain-like (A alternates)"
        return f"Block form ({seq_str})"
    return f"Sectional ({seq_str})"




# ──────────────────────────────────────────────────────────────────────
# Twelve-tone form analysis (row-form-based structural analysis)
# ──────────────────────────────────────────────────────────────────────

NOTE_NAMES = ["C", "C#", "D", "D#", "E", "F",
              "F#", "G", "G#", "A", "A#", "B"]

def generate_all_forms(row_pcs: list[int]) -> dict:
    """Generate all 48 row forms (P₀–₁₁, I₀–₁₁, R₀–₁₁, RI₀–₁₁)."""
    if len(row_pcs) != 12:
        return {}
    pivot = row_pcs[0]
    forms = {}
    for t in range(12):
        p = [(x + t - pivot) % 12 for x in row_pcs]
        forms[f"P{t}"] = p
        i = [(2 * t - x) % 12 for x in p]
        forms[f"I{t}"] = i
        r = list(reversed(p))
        forms[f"R{t}"] = r
        ri = list(reversed(i))
        forms[f"RI{t}"] = ri
    return forms


def identify_row_form(pc_sequence: list[int], all_forms: dict) -> str:
    """Identify which form a 12-PC sequence matches (exact or best)."""
    if len(pc_sequence) != 12:
        return "?"
    seq = list(pc_sequence)
    # Exact match first
    for label, form in all_forms.items():
        if seq == form:
            return label
    return "?"


def get_form_ngrams(all_forms: dict, n: int) -> dict:
    """Extract all overlapping n-grams from each row form.

    Returns {tuple(PCs): [(form_label, position), ...]}
    n=3 for trichords, n=4 for tetrachords, n=6 for hexachords.
    """
    ngram_map = {}
    for label, form in all_forms.items():
        for pos in range(12):
            gram = tuple(form[(pos + i) % 12] for i in range(n))
            ngram_map.setdefault(gram, []).append((label, pos))
    return ngram_map


def print_form_analysis(
    segments: list[AnalysisSegment],
    labels: list[str],
    events: list[NoteEvent],
    row_pcs: list[int] | None,
):
    """Print section-level twelve-tone form analysis.

    Uses 3-note trichord matching: any 3 consecutive notes in the score
    that match a consecutive 3-note segment of a row form are counted
    as evidence of that form being active.
    """
    if not segments or not row_pcs:
        return

    all_forms = generate_all_forms(row_pcs)
    prime_name = NOTE_NAMES[row_pcs[0]]
    print(f"  Source row: P({prime_name}) = {row_pcs}")
    print()

    unique_labels = sorted(set(labels), key=lambda x: labels.index(x))
    sections = {}
    for lbl in unique_labels:
        indices = [i for i, l in enumerate(labels) if l == lbl]
        wins = [segments[i] for i in indices]
        meas = [w.measures for w in wins]
        start_m = min(m[0] for m in meas)
        end_m = max(m[1] for m in meas)
        sections[lbl] = {"start": start_m, "end": end_m}

    # Generate n-gram maps for priority matching: 6 > 4 > 3
    ngram_maps = {n: get_form_ngrams(all_forms, n) for n in [6, 4, 3]}

    section_hits = {lbl: {"P": 0, "I": 0, "R": 0, "RI": 0, "total": 0, "details": []}
                    for lbl in unique_labels}

    # Per-voice analysis with priority matching
    part_events = {}
    for ev in events:
        part_events.setdefault(ev.part_name, []).append(ev)

    for part_name, part_notes in part_events.items():
        part_notes.sort(key=lambda e: e.start_global)
        i = 0
        while i < len(part_notes) - 2:
            best_n = 0
            best_gram = None
            best_matches = []
            for n in [6, 4, 3]:
                if i + n > len(part_notes):
                    continue
                gram = tuple(e.pitch_class for e in part_notes[i:i+n])
                if len(set(gram)) < n:
                    continue
                matches = ngram_maps[n].get(gram, [])
                if matches:
                    best_n = n
                    best_gram = gram
                    best_matches = matches
                    break  # longest match wins
            if best_matches and best_gram:
                meas = part_notes[i].measure
                for lbl in unique_labels:
                    sec = sections[lbl]
                    if sec["start"] <= meas <= sec["end"]:
                        counted_types = set()
                        for form_label, pos in best_matches:
                            if form_label.startswith("RI"):
                                ftype = "RI"
                            else:
                                ftype = form_label[0]
                            if ftype not in counted_types:
                                section_hits[lbl]["details"].append(
                                    (form_label, meas, part_name, ftype, list(best_gram), best_n)
                                )
                                counted_types.add(ftype)
                        break
                i += best_n  # skip past matched window
            else:
                i += 1

    for lbl in unique_labels:
        counts = section_hits[lbl]
        for ftype in ["P", "I", "R", "RI"]:
            counts[ftype] = sum(1 for d in counts["details"] if d[3] == ftype)
        counts["total"] = len(counts["details"])

    first_lbl = unique_labels[0] if unique_labels else None
    last_lbl = unique_labels[-1] if len(unique_labels) > 1 else first_lbl

    print(f"  {'Section':<10} {'Measures':<14} {'P':>5} {'I':>5} {'R':>5} {'RI':>5} {'Total':>6}  {'Function'}")
    print(f"  {'-'*10} {'-'*14} {'-'*5} {'-'*5} {'-'*5} {'-'*5} {'-'*6}  {'-'*20}")

    for lbl in unique_labels:
        info = section_hits[lbl]
        sec = sections[lbl]
        total = info["total"]
 
        if total == 0:
            forms_str = "(none)"
            function = "?"
        else:
            p_pct = info["P"] / total
            i_pct = info["I"] / total
            rri_pct = (info["R"] + info["RI"]) / total

            if lbl == first_lbl:
                function = "Opening (P dominant)" if p_pct > 0.3 else "Opening"
            elif lbl == last_lbl and first_lbl != last_lbl:
                if p_pct > 0.4:
                    function = "Recapitulation (P return)"
                elif rri_pct > 0.5:
                    function = "Closing (retrograde)"
                else:
                    function = "Closing"
            else:
                if i_pct + rri_pct > p_pct * 1.5:
                    function = "Development (I/R contrast)"
                else:
                    function = "Contrast"

        m_str = f"m.{sec['start']}–{sec['end']}"
        print(f"  {lbl:<10} {m_str:<14} {info['P']:>5} {info['I']:>5} {info['R']:>5} {info['RI']:>5} {total:>6}  {function}")

        # Detailed per-form breakdown
        form_entries = {}  # form_label -> {part -> [(measure, pc_set, win_size)]}
        seen_pcs = {}
        for form_label, meas, part, ftype, pc_list, win_size in info["details"]:
            key = (form_label, part, tuple(pc_list))
            if key not in seen_pcs:
                seen_pcs[key] = True
                form_entries.setdefault(form_label, {}).setdefault(part, []).append((meas, pc_list, win_size))
        # Group by form type then measure
        for ftype in ["P", "I", "R", "RI"]:
            type_forms = [(fl, pts) for fl, pts in form_entries.items() if fl.startswith(ftype) or (not fl.startswith("RI") and not fl.startswith("R") and not fl.startswith("I") and fl[0] == ftype)]
            # Actually just check first char for non-RI types
            type_forms = []
            for fl in form_entries:
                if fl.startswith("RI") and ftype == "RI":
                    type_forms.append((fl, form_entries[fl]))
                elif not fl.startswith("RI") and fl[0] == ftype:
                    type_forms.append((fl, form_entries[fl]))
            type_forms.sort(key=lambda x: x[0])
            if type_forms:
                print(f"      {ftype}:")
                for fl, pts in type_forms[:6]:
                    parts_strs = []
                    for pn in sorted(pts):
                        meas_list = sorted(set(m for m, pc, ws in pts[pn]))
                        all_pcs = []
                        for m2, pc2, ws2 in pts[pn]:
                            pc_str = ",".join(map(str, pc2))
                            if pc_str not in all_pcs:
                                all_pcs.append(pc_str)
                        pc_sample = all_pcs[0] if all_pcs else "?"
                        m_range = f"{min(meas_list)}–{max(meas_list)}" if len(meas_list) > 1 else str(meas_list[0])
                        win_label = f"[{pc_sample}](m.{m_range})"
                        parts_strs.append(f"{pn}{win_label}")
                    print(f"        {fl:<6} {', '.join(parts_strs)}")
                if len(type_forms) > 6:
                    print(f"        ... (+{len(type_forms) - 6} more)")
        print()

    print()

if __name__ == "__main__":
    main()

