"""Chord analysis: extract chords from score and classify with Forte system."""

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
    bars = sorted(set(r.bar for r in results))
    lines = [
        f"<!-- v3: {len(results)} chords, {len(bars)} bars -->",
        "",
        "| Bar | Offset | Part Name | Notes | Chord PCs | Normal Order | Prime Form | Forte Class | Pitch Range |",
        "|-----|--------|-----------|-------|-----------|--------------|------------|-------------|-------------|",
    ]
    for bar in bars:
        bar_results = [r for r in results if r.bar == bar]
        for r in bar_results:
            lines.append(
                f"| {r.bar} | {r.offset} | {r.part_name} | "
                f"{r.notes} | {r.pc_set} | {r.normal_order} | {r.prime_form} | {r.forte_class} | {r.pitch_range} |"
            )
        # Add merged row for this bar
        all_pcs = set()
        part_names = set()
        constituents = []
        for r in bar_results:
            all_pcs.update(r.pc_set)
            part_names.add(r.part_name)
            pcs_str = " ".join(map(str, r.pc_set))
            constituents.append(f"[{pcs_str}]({r.part_name})")
        merged_pcs = sorted(all_pcs)
        if len(merged_pcs) > 1:
            c = chord.Chord(merged_pcs)
            merged_notes = "merged: " + " + ".join(constituents)
            lines.append(
                f"| {bar} | merged | {'/'.join(sorted(part_names))} | "
                f"{merged_notes} | {list(c.normalOrder)} | {list(c.normalOrder)} | {c.primeFormString} | {c.forteClass} | |"
            )
    return "\n".join(lines)


def format_as_csv(results: list[ChordResult]) -> str:
    """Format chord analysis results as CSV."""
    lines = ["Bar,Offset,Part Name,Notes,Chord PCs,Normal Order,Prime Form,Forte Class,Pitch Range"]
    for r in results:
        lines.append(
            f'{r.bar},{r.offset},"{r.part_name}","{r.notes}",'
            f'"{r.pc_set}","{r.normal_order}","{r.prime_form}","{r.forte_class}","{r.pitch_range}"'
        )
    return "\n".join(lines)
