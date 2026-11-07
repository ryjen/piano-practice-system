"""Deterministic, offline MusicXML exports compatible with PianGo.

The catalog stores MIDI pitches in performance order, not general-purpose scores.
Two coordination exercises have explicitly modeled hand timelines. All others
are exported as sequential drills, matching the catalog's reference sequences.
Nothing in this exporter asserts observed fingering or hand identity.
"""
from __future__ import annotations

import re
import xml.etree.ElementTree as ET

from .core import validate_catalog
from .timeline import onset_groups

STEPS = {"C": 0, "D": 2, "E": 4, "F": 5, "G": 7, "A": 9, "B": 11}
DEFAULT = ("C", "C#", "D", "Eb", "E", "F", "F#", "G", "Ab", "A", "Bb", "B")

# Spellings are authored exercise references; pitches are checked against MIDI.
SPELLINGS = {
    "reading-accidentals": ("C4", "C#4", "D4", "Eb4", "E4", "F4", "E4", "Eb4", "D4", "C#4", "C4"),
    "minor-natural": ("A3", "B3", "C4", "D4", "E4", "F4", "G4", "A4"),
    "minor-harmonic": ("A3", "B3", "C4", "D4", "E4", "F4", "G#4", "A4"),
    "circle-fourths": ("C4", "F4", "Bb4", "Eb4", "Ab4", "Db4", "Gb4", "B4", "E4", "A4", "D4", "G4", "C4"),
    "circle-fifths": ("C4", "G4", "D4", "A4", "E4", "B4", "F#4", "Db4", "Ab4", "Eb4", "Bb4", "F4", "C4"),
}

# Optional, *illustrative* RIGHT-hand choices, not measured performance
# or assertions of one ideal fingering for every hand size or phrase.
FINGERING_REFERENCES = {
    "reading-staff-steps": (1, 2, 3, 4, 5),
    "navigation-steps": (1, 2, 3, 4, 5, 4, 3, 2, 1),
    "minor-natural": (1, 2, 3, 1, 2, 3, 4, 5),
    "minor-harmonic": (1, 2, 3, 1, 2, 3, 4, 5),
}


def _spellings(exercise: dict) -> list[str]:
    notes = exercise["notes"]
    spellings = list(SPELLINGS.get(
        exercise["id"], tuple(DEFAULT[n % 12] + str(n // 12 - 1) for n in notes)
    ))
    if len(spellings) != len(notes):
        raise ValueError("exercise spelling length differs from note sequence")
    for spelling, midi in zip(spellings, notes):
        match = re.fullmatch(r"([A-G])([#b]?)(-?[0-9]+)", spelling)
        if match is None:
            raise ValueError("invalid written note spelling")
        step, mark, octave = match.groups()
        actual = (int(octave) + 1) * 12 + STEPS[step] + (1 if mark == "#" else -1 if mark == "b" else 0)
        if actual != midi:
            raise ValueError("written note spelling disagrees with MIDI catalog")
    return spellings


def _parts(exercise: dict, spellings: list[str]) -> list[tuple[str, str, str, list[str | None]]]:
    # Render both hand timelines from the same versioned onset groups used
    # for MIDI assessment. Legacy sequential drills keep a single staff.
    if exercise.get("realization") is None:
        return [("P1", "Piano (right-hand reference)", "G", spellings)]
    right, left = [], []
    cursor = 0
    for group in onset_groups(exercise):
        span = len(group["pitches"])
        written = spellings[cursor:cursor + span]
        cursor += span
        by_hand = dict(zip(group["hands"], written))
        right.append(by_hand.get("right"))
        left.append(by_hand.get("left"))
    if cursor != len(spellings):
        raise ValueError("score realization and spelling length disagree")
    return [
        ("P1", "Right hand", "G", right),
        ("P2", "Left hand", "F", left),
    ]


def _write_note(measure: ET.Element, spelling: str | None,
                duration: int, kind: str, finger: int | None = None) -> None:
    note = ET.SubElement(measure, "note")
    if spelling is None:
        ET.SubElement(note, "rest")
    else:
        match = re.fullmatch(r"([A-G])([#b]?)(-?[0-9]+)", spelling)
        if match is None:
            raise ValueError("invalid written note spelling")
        step, mark, octave = match.groups()
        pitch = ET.SubElement(note, "pitch")
        ET.SubElement(pitch, "step").text = step
        if mark:
            ET.SubElement(pitch, "alter").text = "1" if mark == "#" else "-1"
        ET.SubElement(pitch, "octave").text = octave
    ET.SubElement(note, "duration").text = str(duration)
    ET.SubElement(note, "type").text = kind
    if spelling is not None and mark:
        ET.SubElement(note, "accidental").text = "sharp" if mark == "#" else "flat"
    if finger is not None:
        notations = ET.SubElement(note, "notations")
        technical = ET.SubElement(notations, "technical")
        ET.SubElement(technical, "fingering").text = str(finger)


def to_piango_musicxml(catalog: dict, exercise_id: str,
                      *, fingering_reference: bool = False) -> str:
    """Render one public original exercise; never accesses a network or learner state.

    Missing fingerings are deliberately left for PianGo's suggestion engine.
    No generated fingering is interpreted as a measurement of the player's hand.
    """
    validate_catalog(catalog)
    ex = next((e for e in catalog["exercises"] if e["id"] == exercise_id), None)
    if ex is None:
        raise ValueError("unknown exercise")
    spellings = _spellings(ex)
    parts = _parts(ex, spellings)
    subdivision = ex["subdivision"]
    # All current coordination exercises are quarter-note reference drills.
    if len(parts) > 1 and subdivision != 1:
        raise ValueError("poly-hand export requires quarter-note subdivision")
    per_measure = 4 * subdivision
    duration = 2 if subdivision == 1 else 1
    kind = "quarter" if subdivision == 1 else "eighth"
    fingers = FINGERING_REFERENCES.get(exercise_id) if fingering_reference else None
    if fingers is not None and (len(parts) != 1 or len(fingers) != len(spellings)):
        raise ValueError("fingering reference does not fit exercise")
    root = ET.Element("score-partwise", version="4.0")
    work = ET.SubElement(root, "work")
    ET.SubElement(work, "work-title").text = "Original practice: " + ex["title"]
    ET.SubElement(root, "movement-title").text = ex["title"]
    part_list = ET.SubElement(root, "part-list")
    for part_id, part_name, _, _ in parts:
        entry = ET.SubElement(part_list, "score-part", id=part_id)
        ET.SubElement(entry, "part-name").text = part_name
    for part_index, (part_id, _, clef_sign, events) in enumerate(parts):
        part = ET.SubElement(root, "part", id=part_id)
        for index, start in enumerate(range(0, len(events), per_measure), 1):
            measure = ET.SubElement(part, "measure", number=str(index))
            if index == 1:
                attrs = ET.SubElement(measure, "attributes")
                ET.SubElement(attrs, "divisions").text = "2"
                key = ET.SubElement(attrs, "key")
                ET.SubElement(key, "fifths").text = "0"
                time = ET.SubElement(attrs, "time")
                ET.SubElement(time, "beats").text = "4"
                ET.SubElement(time, "beat-type").text = "4"
                clef = ET.SubElement(attrs, "clef")
                ET.SubElement(clef, "sign").text = clef_sign
                ET.SubElement(clef, "line").text = "4" if clef_sign == "F" else "2"
                if part_index == 0:
                    direction = ET.SubElement(measure, "direction")
                    dtype = ET.SubElement(direction, "direction-type")
                    metro = ET.SubElement(dtype, "metronome")
                    ET.SubElement(metro, "beat-unit").text = "quarter"
                    ET.SubElement(metro, "per-minute").text = str(ex["bpm"])
                    ET.SubElement(direction, "sound", tempo=str(ex["bpm"]))
            for event_index in range(start, start + per_measure):
                written = events[event_index] if event_index < len(events) else None
                finger = fingers[event_index] if fingers is not None and event_index < len(fingers) else None
                _write_note(measure, written, duration, kind, finger)
    ET.indent(root)
    return '<?xml version="1.0" encoding="utf-8"?>\n' + ET.tostring(root, encoding="unicode") + "\n"
