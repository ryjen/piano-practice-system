"""Generate original single-voice MusicXML drills from public note sequences.

MusicXML is an exercise artifact, not a transcription of Alfred repertoire.
Only exercises with reading/minor-technique focus are exported here.
"""
from __future__ import annotations

import xml.etree.ElementTree as ET

from .core import validate_catalog

# Explicit spellings are preferable to assuming a sharp for every black key.
READING_SPELLINGS = {
    "reading-accidentals": ["C4", "C#4", "D4", "Eb4", "E4", "F4", "E4", "Eb4", "D4", "C#4", "C4"],
    "minor-harmonic": ["A3", "B3", "C4", "D4", "E4", "F4", "G#4", "A4"]
}
STEPS = {"C": 0, "D": 2, "E": 4, "F": 5, "G": 7, "A": 9, "B": 11}
DEFAULT = ("C", "C#", "D", "Eb", "E", "F", "F#", "G", "Ab", "A", "Bb", "B")


def spelling_to_midi(spelling: str) -> int:
    if not isinstance(spelling, str) or len(spelling) not in (2, 3):
        raise ValueError("invalid pitch spelling")
    letter = spelling[0]
    if letter not in STEPS or not spelling[-1].isdigit():
        raise ValueError("invalid pitch spelling")
    mark = spelling[1:-1]
    if mark not in ("", "#", "b"):
        raise ValueError("unsupported pitch accidental")
    return (int(spelling[-1]) + 1) * 12 + STEPS[letter] + (1 if mark == "#" else -1 if mark == "b" else 0)


def to_musicxml(catalog: dict, exercise_id: str) -> str:
    validate_catalog(catalog)
    exercise = next((e for e in catalog["exercises"] if e["id"] == exercise_id), None)
    if exercise is None:
        raise ValueError("unknown exercise")
    if exercise["technique_id"] not in ("reading", "minor"):
        raise ValueError("notation output supports reading and minor exercises only")
    notes = exercise["notes"]
    spellings = READING_SPELLINGS.get(exercise_id)
    if spellings is None:
        spellings = [DEFAULT[n % 12] + str(n // 12 - 1) for n in notes]
    if len(spellings) != len(notes) or any(spelling_to_midi(s) != n for s, n in zip(spellings, notes)):
        raise ValueError("declared notation spellings do not match MIDI pitch numbers")

    root = ET.Element("score-partwise", version="4.0")
    work = ET.SubElement(root, "work")
    ET.SubElement(work, "work-title").text = "Original practice: " + exercise["title"]
    ET.SubElement(root, "movement-title").text = exercise["title"]
    parts = ET.SubElement(root, "part-list")
    score_part = ET.SubElement(parts, "score-part", id="P1")
    ET.SubElement(score_part, "part-name").text = "Piano"
    part = ET.SubElement(root, "part", id="P1")
    for bar_number, offset in enumerate(range(0, len(spellings), 4), 1):
        measure = ET.SubElement(part, "measure", number=str(bar_number))
        if bar_number == 1:
            attrs = ET.SubElement(measure, "attributes")
            ET.SubElement(attrs, "divisions").text = "1"
            time = ET.SubElement(attrs, "time")
            ET.SubElement(time, "beats").text = "4"
            ET.SubElement(time, "beat-type").text = "4"
            clef = ET.SubElement(attrs, "clef")
            ET.SubElement(clef, "sign").text = "G"
            ET.SubElement(clef, "line").text = "2"
            direction = ET.SubElement(measure, "direction")
            dtype = ET.SubElement(direction, "direction-type")
            metro = ET.SubElement(dtype, "metronome")
            ET.SubElement(metro, "beat-unit").text = "quarter"
            ET.SubElement(metro, "per-minute").text = str(exercise["bpm"])
        for spelling in spellings[offset:offset + 4]:
            note = ET.SubElement(measure, "note")
            pitch = ET.SubElement(note, "pitch")
            ET.SubElement(pitch, "step").text = spelling[0]
            mark = spelling[1:-1]
            if mark:
                ET.SubElement(pitch, "alter").text = str(1 if mark == "#" else -1)
            ET.SubElement(pitch, "octave").text = spelling[-1]
            ET.SubElement(note, "duration").text = "1"
            ET.SubElement(note, "type").text = "quarter"
            if mark:
                ET.SubElement(note, "accidental").text = "sharp" if mark == "#" else "flat"
        for _ in range(4 - len(spellings[offset:offset + 4])):
            note = ET.SubElement(measure, "note")
            ET.SubElement(note, "rest")
            ET.SubElement(note, "duration").text = "1"
            ET.SubElement(note, "type").text = "quarter"
    ET.indent(root)
    # Avoid an external DTD dependency; the score is self-contained for offline use.
    return '<?xml version="1.0" encoding="utf-8"?>\n' + ET.tostring(root, encoding="unicode") + "\n"
