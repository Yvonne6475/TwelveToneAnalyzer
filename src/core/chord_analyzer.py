"""Chord analysis: extract chords from score and classify with Forte system."""

import csv
import io
from dataclasses import dataclass, field
from music21 import chord, note, converter


@dataclass
class ChordResult:
    bar: int
    offset: float
    part_name: str
    notes: str
    pc_set: list[int]
    normal_order: list[int]
    prime_form: str
    forte_class: str
    pitch_range: str


def build_display_rows(results: list[ChordResult]) -> list[dict]:
    """Build the same ordered rows shown in the Chord Analysis table."""
    bar_groups = {}
    for r in results:
        bar_groups.setdefault(r.bar, []).append(r)

    part_order = []
    seen = set()
    for r in results:
        if r.part_name not in seen:
            seen.add(r.part_name)
            part_order.append(r.part_name)

    rows = []
    for bar in sorted(bar_groups):
        bar_rs = bar_groups[bar]

        for r in bar_rs:
            rows.append({
                "kind": "indiv",
                "bar": r.bar,
                "offset": r.offset,
                "offset_num": r.offset,
                "part_name": r.part_name,
                "notes": r.notes,
                "pc_set": str(r.pc_set),
                "pcs": list(r.pc_set),
                "normal_order": str(r.normal_order),
                "prime_form": r.prime_form,
                "forte_class": r.forte_class,
                "pitch_range": r.pitch_range,
            })

        # Per-part merged (in first-appearance part order)
        part_pcs = {}
        for r in bar_rs:
            part_pcs.setdefault(r.part_name, []).extend(r.pc_set)
        for pn in part_order:
            if pn not in part_pcs:
                continue
            uniq = list(dict.fromkeys(part_pcs[pn]))
            if len(uniq) > 1:
                c = chord.Chord(sorted(uniq))
                rows.append({
                    "kind": "part_merged",
                    "bar": bar,
                    "offset": f"{pn} merged",
                    "part_name": pn,
                    "notes": str(uniq),
                    "pc_set": str(uniq),
                    "pcs": uniq,
                    "normal_order": str(list(c.normalOrder)),
                    "prime_form": c.primeFormString,
                    "forte_class": c.forteClass,
                    "pitch_range": "",
                })

        # Bar merged (first-occurrence pitch-class order)
        merged_pcs = []
        seen_pcs = set()
        for r in bar_rs:
            for pc in r.pc_set:
                if pc not in seen_pcs:
                    seen_pcs.add(pc)
                    merged_pcs.append(pc)
        if len(merged_pcs) > 1:
            c = chord.Chord(merged_pcs)
            rows.append({
                "kind": "merged",
                "bar": bar,
                "offset": f"merged (bar {bar})",
                "part_name": "\\n".join(sorted(set(r.part_name for r in bar_rs))),
                "notes": f"merged: {' '.join(map(str, merged_pcs))}",
                "pc_set": str(merged_pcs),
                "pcs": merged_pcs,
                "normal_order": str(list(c.normalOrder)),
                "prime_form": c.primeFormString,
                "forte_class": c.forteClass,
                "pitch_range": "",
            })

        # Offset merged (one row per offset with multiple parts)
        off_groups = {}
        for r in bar_rs:
            off_groups.setdefault(r.offset, []).append(r)
        for off in sorted(off_groups):
            rs = off_groups[off]
            if len(rs) <= 1:
                continue
            parts_list_o = []
            for r in rs:
                uniq = list(dict.fromkeys(r.pc_set))
                parts_list_o.append(f"{r.part_name}[{' '.join(map(str, uniq))}]")
            merged_o = []
            seen_o = set()
            for r in rs:
                for pc in r.pc_set:
                    if pc not in seen_o:
                        seen_o.add(pc)
                        merged_o.append(pc)
            if len(merged_o) > 1:
                c = chord.Chord(merged_o)
                rows.append({
                    "kind": "offset_merged",
                    "bar": bar,
                    "offset": f"offset {off}",
                    "part_name": " + ".join(parts_list_o),
                    "notes": str(merged_o),
                    "pc_set": str(merged_o),
                    "pcs": merged_o,
                    "normal_order": str(list(c.normalOrder)),
                    "prime_form": c.primeFormString,
                    "forte_class": c.forteClass,
                    "pitch_range": "",
                })

    return rows


def _get_staff(el) -> int:
    """Return the staff index (1-based) for a note/chord, defaulting to 1."""
    for attr in ('staffIndex', '_staffIndex'):
        val = getattr(el, attr, None)
        if val is not None:
            return val
    return 1


def extract_chords(score, selected, bar_range: tuple,
                   name_map: dict = None) -> list[ChordResult]:
    """Extract chords and single notes from selected (part_idx, staff_idx) pairs and measure range."""
    results = []
    start_bar, end_bar = bar_range
    if name_map is None:
        name_map = {}

    for part_idx, part in enumerate(score.parts):
        part_name = part.partName if part.partName else f"Part {part_idx + 1}"

        meas_all = list(part.getElementsByClass('Measure'))
        meas_range = [m for m in meas_all if start_bar <= m.number <= end_bar]
        if not meas_range:
            continue
        for _i in range(1, len(meas_range)):
            if meas_range[_i].getOffsetBySite(part) - meas_range[_i-1].getOffsetBySite(part) > 50:
                meas_range = meas_range[:_i]
                break
        for measure in meas_range:
            bar_number = measure.number

            for element in measure.recurse():
                is_chord = isinstance(element, chord.Chord)
                is_note = isinstance(element, note.Note)
                if not is_chord and not is_note:
                    continue

                staff_idx = _get_staff(element)
                if selected and (part_idx, staff_idx) not in selected:
                    continue

                key = (part_idx, staff_idx)
                qual_name = name_map.get(key, name_map.get((part_idx, 1), part_name))
                if staff_idx > 1 and key not in name_map:
                    qual_name = f"{part_name} (Staff {staff_idx})"

                if is_note:
                    pitches = [element.pitch]
                    notes_str = element.pitch.nameWithOctave  # single note, no sorting needed
                    # Wrap single note as chord for Forte/normalOrder
                    c = chord.Chord([element.pitch])
                    pc_set = [element.pitch.pitchClass]
                    normal_order = list(c.normalOrder)
                    prime_form = c.primeFormString
                    forte_class = c.forteClass
                else:
                    pitches = element.pitches
                    # Explicit descending order by MIDI (highest pitch first)
                    pitches_desc = sorted(pitches, key=lambda p: -p.midi)
                    notes_str = " ".join(p.nameWithOctave for p in pitches_desc)
                    pc_set = [p.pitchClass for p in pitches_desc]
                    normal_order = list(element.normalOrder)
                    prime_form = element.primeFormString
                    forte_class = element.forteClass

                pitch_min = min(p.midi for p in pitches)
                pitch_max = max(p.midi for p in pitches)

                results.append(ChordResult(
                    bar=bar_number,
                    offset=round(element.offset, 3),
                    part_name=qual_name,
                    notes=notes_str,
                    pc_set=pc_set,
                    normal_order=normal_order,
                    prime_form=prime_form,
                    forte_class=forte_class,
                    pitch_range=f"{pitch_min}~{pitch_max}",
                ))

    return results


def format_as_markdown(results: list[ChordResult]) -> str:
    """Format chord analysis results as a Markdown table."""
    rows = build_display_rows(results)
    bars = sorted({row["bar"] for row in rows})
    lines = [
        f"<!-- v3: {len(results)} chords, {len(bars)} bars -->",
        "",
        "| Bar | Offset | Part Name | Notes | Chords PCs | Normal Order | Prime Form | Forte Class | Pitch Range |",
        "|-----|--------|-----------|-------|-----------|--------------|------------|-------------|-------------|",
    ]
    for row in rows:
        lines.append(
            f"| {row['bar']} | {row['offset']} | {row['part_name']} |"
            f" {row['notes']} | {row['pc_set']} |"
            f" {row['normal_order']} | {row['prime_form']} | {row['forte_class']} | {row['pitch_range']} |"
        )
    return "\n".join(lines)


def format_as_csv(results: list[ChordResult]) -> str:
    """Format chord analysis results as CSV."""
    def excel_text(value: str) -> str:
        """Keep values like '1-1' from being interpreted as dates by Excel."""
        return f'="{value}"'

    output = io.StringIO()
    writer = csv.writer(output, lineterminator="\n")
    writer.writerow([
        "Bar", "Offset", "Part Name", "Notes", "Chord PCs", "Normal Order",
        "Prime Form", "Forte Class", "Pitch Range",
    ])
    for row in build_display_rows(results):
        writer.writerow([
            row["bar"], row["offset"], row["part_name"], row["notes"],
            row["pc_set"], row["normal_order"], row["prime_form"],
            excel_text(row["forte_class"]), row["pitch_range"],
        ])
    return output.getvalue()
