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

        for measure in part.getElementsByClass('Measure'):
            bar_number = measure.number
            if not (start_bar <= bar_number <= end_bar):
                continue

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
                    notes_str = element.pitch.nameWithOctave
                    # Wrap single note as chord for Forte/normalOrder
                    c = chord.Chord([element.pitch])
                    pc_set = list(c.normalOrder)
                    forte_class = c.forteClass
                else:
                    pitches = element.pitches
                    notes_str = " ".join(p.nameWithOctave for p in pitches)
                    pc_set = list(element.normalOrder)
                    forte_class = element.forteClass

                pitch_min = min(p.midi for p in pitches)
                pitch_max = max(p.midi for p in pitches)

                results.append(ChordResult(
                    bar=bar_number,
                    offset=round(element.offset, 3),
                    part_name=qual_name,
                    notes=notes_str,
                    pc_set=pc_set,
                    forte_class=forte_class,
                    pitch_range=f"{pitch_min}~{pitch_max}",
                ))

    return results


def format_as_markdown(results: list[ChordResult]) -> str:
    """Format chord analysis results as a Markdown table."""
    lines = [
        "| Bar | Offset | Part Name | Notes | Normal Order | Forte Class | Pitch Range |",
        "|-----|--------|-----------|-------|--------------|-------------|-------------|",
    ]
    for r in results:
        lines.append(
            f"| {r.bar} | {r.offset} | {r.part_name} | "
            f"{r.notes} | {r.pc_set} | {r.forte_class} | {r.pitch_range} |"
        )
    return "\n".join(lines)


def format_as_csv(results: list[ChordResult]) -> str:
    """Format chord analysis results as CSV."""
    lines = ["Bar,Offset,Part Name,Notes,Normal Order,Forte Class,Pitch Range"]
    for r in results:
        lines.append(
            f'{r.bar},{r.offset},"{r.part_name}","{r.notes}",'
            f'"{r.pc_set}","{r.forte_class}","{r.pitch_range}"'
        )
    return "\n".join(lines)
