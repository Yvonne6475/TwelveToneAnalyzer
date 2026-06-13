"""Twelve-tone row operations: P/I/R/RI forms, matrix, row grouping."""

import numpy as np
from music21 import serial, stream, note, chord, metadata


def generate_forms(row: list[int]) -> dict:
    """Generate P, R, I, RI forms of a twelve-tone row.
    Returns dict with keys like 'P6', 'R6', 'I6', 'RI6'.
    """
    pivot = row[0]
    p_row = list(row)
    r_row = list(reversed(row))
    i_row = [(2 * pivot - p) % 12 for p in p_row]
    ri_row = [(2 * pivot - p) % 12 for p in r_row]

    return {
        f"P{p_row[0]}": p_row,
        f"R{r_row[0]}": r_row,
        f"I{i_row[0]}": i_row,
        f"RI{ri_row[0]}": ri_row,
    }


def generate_matrix(row: list[int]) -> np.ndarray:
    """Generate a 12x12 twelve-tone matrix."""
    matrix = np.zeros((12, 12), dtype=int)
    matrix[0, :] = row
    for i in range(1, 12):
        interval = (row[i] - row[0]) % 12
        for j in range(12):
            matrix[i, j] = (row[j] - interval) % 12
    return matrix


def make_row_stream(pc_list: list[int], name: str, base_midi: int = 60) -> stream.Part:
    """Create a music21 Part from a pitch-class list."""
    s = stream.Part()
    s.insert(0, metadata.Metadata())
    s.metadata.title = name
    for pc in pc_list:
        n = note.Note()
        n.pitch.midi = pc + base_midi
        n.quarterLength = 1
        n.addLyric(str(pc))
        n.addLyric(n.pitch.name)
        s.append(n)
    return s


def divide_into_chords(row: list[int], group_size: int) -> list:
    """Divide a 12-tone row into chords of equal group_size.
    Returns list of (notes, primeFormString, forteClass).
    """
    chords = []
    for i in range(0, 12, group_size):
        group = row[i:i + group_size]
        c = chord.Chord(group)
        chords.append({
            "notes": group,
            "prime_form": c.primeFormString,
            "forte_class": c.forteClass,
        })
    return chords


def make_group_stream(groups: list, title: str = "Row Groups") -> stream.Part:
    """Create a music21 Part from chord groups (trichords/tetrachords/hexachords)."""
    s = stream.Part()
    s.insert(0, metadata.Metadata())
    s.metadata.title = title
    for g in groups:
        c = chord.Chord(g["notes"])
        c.addLyric(str(c.primeFormString))
        c.addLyric(c.forteClass)
        c.quarterLength = 2
        s.append(c)
    return s


def create_12tone_matrix(row: list[int]) -> serial.TwelveToneRow:
    """Create a music21 TwelveToneRow object."""
    return serial.TwelveToneRow(row)
