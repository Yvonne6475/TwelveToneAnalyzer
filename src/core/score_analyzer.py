"""Score analysis: voice diagnosis, pitch extraction, and measure utilities."""

from __future__ import annotations

from dataclasses import dataclass
from music21 import note, chord, stream


@dataclass
class PartDiagnosis:
    index: int
    part_name: str
    note_count: int
    note_only_count: int
    chord_count: int
    avg_pitch: float | None
    pitch_range: tuple | None
    staff_count: int
    instruments: list[str]


def diagnose_part(part, index: int) -> PartDiagnosis:
    notes = [n for n in part.recurse().notes]
    pitches = [n.pitch.midi for n in notes if n.isNote]

    return PartDiagnosis(
        index=index,
        part_name=part.partName if part.partName else "Unnamed",
        note_count=len(notes),
        note_only_count=len([n for n in notes if n.isNote]),
        chord_count=len([n for n in notes if n.isChord]),
        avg_pitch=round(sum(pitches) / len(pitches), 2) if pitches else None,
        pitch_range=(min(pitches), max(pitches)) if pitches else None,
        staff_count=len(part.getElementsByClass('Staff')),
        instruments=[i.instrumentName for i in part.getInstruments() if i.instrumentName],
    )


def diagnose_all_parts(score) -> list[PartDiagnosis]:
    diagnostics = []
    try:
        for i, part in enumerate(score.parts):
            d = diagnose_part(part, i)
            diagnostics.append(d)
    except (AttributeError, IndexError):
        # Score has no parts (single-part score) or parts iterator failed
        d = diagnose_part(score, 0)
        diagnostics.append(d)
    return diagnostics


def get_measure_range(score) -> tuple:
    measures = []
    try:
        for part in score.parts:
            measures.extend(part.getElementsByClass('Measure'))
    except (AttributeError, IndexError):
        pass
    if not measures:
        try:
            measures = list(score.flatten().getElementsByClass('Measure'))
        except Exception:
            pass
    if measures:
        nums = [m.number for m in measures if m.number is not None]
        if nums:
            return min(nums), max(nums)
    return 1, 272


def extract_first_n_notes(part, n: int = 12) -> list[tuple]:
    """Extract first n notes/chords from a part as (name, pitchClass) tuples."""
    result = []
    for el in part.recurse():
        if isinstance(el, note.Note):
            result.append((el.pitch.name, el.pitch.pitchClass))
        elif isinstance(el, chord.Chord):
            top = el.sortAscending()[-1]
            result.append((top.name, top.pitchClass))
        if len(result) >= n:
            break
    return result


def auto_select_melody_part(score, diagnostics: list[PartDiagnosis]) -> int:
    """Return the index of the part with the most single notes."""
    melody_candidates = [
        (i, d.note_only_count)
        for i, d in enumerate(diagnostics)
    ]
    return max(melody_candidates, key=lambda x: x[1])[0]


def annotate_score(score, start_measure: int, end_measure: int):
    """Add pitch class and Forte class lyrics to an excerpt of the score."""
    excerpt = score.measures(start_measure, end_measure)
    _add_pc_forte_lyrics(excerpt)
    return excerpt


def _add_pc_forte_lyrics(stream):
    """Add pitch-class and Forte lyrics to an existing stream. Modifies in place."""
    for n in stream.recurse().notes:
        if isinstance(n, note.Note):
            n.addLyric(str(n.pitch.pitchClass))
            n.addLyric(n.nameWithOctave)
        elif isinstance(n, chord.Chord):
            sorted_pitches = sorted(n.pitches)
            for p in sorted_pitches:
                n.addLyric(str(p.pitchClass))
                n.addLyric(p.nameWithOctave)
            n.addLyric(n.forteClass)


def annotate_score_full(score):
    """Annotate the full score with pitch class and Forte class lyrics (for MEI files)."""
    _add_pc_forte_lyrics(score)
    return score


def strip_annotations(score):
    """Remove lyrics, dynamics, tempo, articulations, slurs, ties, and expressions.

    Tuplets are intentionally preserved — they are rhythmic/meter elements,
    not annotations.
    """
    from music21 import dynamics, spanner, tie, tempo, articulations

    for n in score.recurse().notes:
        for ly in list(getattr(n, 'lyrics', [])):
            n.lyrics.remove(ly)
        n.expressions = []
        if n.tie:
            n.tie = None

    to_remove = []
    for el in score.recurse():
        name = type(el).__name__.lower()
        if isinstance(el, (dynamics.Dynamic,
                           tempo.MetronomeMark, tempo.TempoText,
                           articulations.Articulation,
                           spanner.Slur, tie.Tie)):
            to_remove.append(el)
        elif 'crescendo' in name or 'diminuendo' in name:
            to_remove.append(el)
    for el in to_remove:
        if el.activeSite:
            el.activeSite.remove(el)


def clean_xml_presentation(xml_path: str):
    """Remove slurs, ties, dynamics, wedges, and words from a MusicXML file.

    Preserves <lyric> (pitch-class annotations) and <tuplet> (rhythmic notation).
    Used as a safety net after MusicXML export to catch any spanner elements
    that were missed or left in an inconsistent state by Python-level removal.
    """
    import re

    with open(xml_path, 'r', encoding='utf-8') as f:
        content = f.read()

    content = re.sub(r'<slur\b[^>]*/?>', '', content)
    content = re.sub(r'<tied\b[^>]*/?>', '', content)
    content = re.sub(r'<dynamics\b[^>]*>.*?</dynamics>', '', content, flags=re.DOTALL)
    content = re.sub(r'<dynamics\b[^>]*/>', '', content)
    content = re.sub(r'<wedge\b[^>]*>.*?</wedge>', '', content, flags=re.DOTALL)
    content = re.sub(r'<wedge\b[^>]*/>', '', content)
    content = re.sub(r'<words\b[^>]*>.*?</words>', '', content, flags=re.DOTALL)
    content = re.sub(r'<words\b[^>]*/>', '', content)
    content = re.sub(r'<direction[^>]*>\s*</direction>', '', content)
    content = re.sub(r'<direction\s*/>', '', content)
    content = re.sub(r'<notations[^>]*>\s*</notations>', '', content)

    with open(xml_path, 'w', encoding='utf-8') as f:
        f.write(content)


def clean_musicxml(xml_path: str):
    """Post-process a MusicXML file to remove lyrics, dynamics, slurs, and ties."""
    import re

    with open(xml_path, 'r', encoding='utf-8') as f:
        content = f.read()

    # Remove <lyric> blocks (including multi-line)
    content = re.sub(r'<lyric\b[^>]*>.*?</lyric>', '', content, flags=re.DOTALL)
    content = re.sub(r'<lyric\b[^>]*/>', '', content)

    # Remove <dynamics> blocks
    content = re.sub(r'<dynamics\b[^>]*>.*?</dynamics>', '', content, flags=re.DOTALL)
    content = re.sub(r'<dynamics\b[^>]*/>', '', content)

    # Remove <slur> elements
    content = re.sub(r'<slur\b[^>]*/?>', '', content)

    # Remove <tied> elements
    content = re.sub(r'<tied\b[^>]*/?>', '', content)

    # Remove <wedge> (crescendo/diminuendo) blocks
    content = re.sub(r'<wedge\b[^>]*>.*?</wedge>', '', content, flags=re.DOTALL)
    content = re.sub(r'<wedge\b[^>]*/>', '', content)

    # Remove <words> (text expressions) blocks
    content = re.sub(r'<words\b[^>]*>.*?</words>', '', content, flags=re.DOTALL)
    content = re.sub(r'<words\b[^>]*/>', '', content)

    # Remove empty <direction> elements left after stripping
    content = re.sub(r'<direction[^>]*>\s*</direction>', '', content)
    content = re.sub(r'<direction\s*/>', '', content)

    # Remove empty <notations> elements
    content = re.sub(r'<notations[^>]*>\s*</notations>', '', content)

    with open(xml_path, 'w', encoding='utf-8') as f:
        f.write(content)


def export_annotated_score(score, score_path: str, output_dir: str,
                           start_measure: int, end_measure: int,
                           parent=None) -> str:
    """Export annotated score as MusicXML, PDF, and open viewer. Returns base filename."""
    import os
    from pathlib import Path
    from datetime import datetime

    os.makedirs(output_dir, exist_ok=True)
    excerpt = annotate_score(score, start_measure, end_measure)

    piece_name = Path(score_path).stem if score_path else "analysis"
    date_str = datetime.now().strftime("%Y%m%d")
    base = f"{piece_name}_m{start_measure}-{end_measure}_pc_forte_{date_str}"

    xml_path = os.path.join(output_dir, f"{base}.musicxml")
    pdf_path = os.path.join(output_dir, f"{base}.pdf")

    excerpt.write('musicxml', xml_path)
    try:
        excerpt.write('musicxml.pdf', pdf_path)
    except Exception:
        pass  # PDF export requires MuseScore

    excerpt.show()

    from PyQt5.QtWidgets import QMessageBox
    from src.utils.i18n import tr
    msg = tr("dialog.export_annotated_msg", xml=xml_path, pdf=pdf_path if os.path.exists(pdf_path) else "N/A")
    QMessageBox.information(parent, tr("dialog.export_complete"), msg)
    return base
