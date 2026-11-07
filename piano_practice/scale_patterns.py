"""Original C-major paired-hand scale exercises and five-phase pattern.

These are illustrative written notes, not a claim about the player's exact
register, confirmed fingering, or measured physical performance.
"""
from __future__ import annotations

STEPS = (0, 2, 4, 5, 7, 9, 11)


def c_major(base_c: int, degree: int) -> int:
    """Map signed C-major scale degrees to MIDI numbers (supports descent)."""
    octave, offset = divmod(degree, 7)
    note = base_c + 12 * octave + STEPS[offset]
    if not 0 <= note <= 127:
        raise ValueError("C-major scale degree outside MIDI range")
    return note


def hands_together_two_octaves() -> dict:
    """Two-octave parallel ascending C-major practice; two hands throughout."""
    groups = [
        {"pitches": [c_major(48, i), c_major(60, i)],
         "hands": ["left", "right"]}
        for i in range(15)
    ]
    return {
        "contract_version": "onset-groups/v1",
        "onsets": groups,
        "phases": [{
            "id": "parallel-two-octaves",
            "label": "Hands together up two octaves",
            "start": 0, "end": len(groups)
        }],
        "finger_cues": [
            {"onset_index": 5, "hand": "left", "finger": 3,
             "label": "LH crossing to finger 3 in octave one"},
            {"onset_index": 8, "hand": "left", "finger": 4,
             "label": "LH crossing to finger 4 in octave two"}
        ]
    }


def five_phase_opposing_scales() -> dict:
    """Provisional C-major realization of the player's described five phases.

    Phases: 1 parallel up; 2 LH reverse as RH rises then returns; 3 parallel
    up and return; 4 contrary out and return; 5 parallel down. Each update
    adds one beat of intended LH/RH notes; when LH pauses, RH alone plays.
    """
    groups: list[dict] = []
    phases: list[dict] = []

    def append(lh_degree: int | None, rh_degree: int | None) -> None:
        pitches = []
        hands = []
        if lh_degree is not None:
            pitches.append(c_major(48, lh_degree))
            hands.append("left")
        if rh_degree is not None:
            pitches.append(c_major(60, rh_degree))
            hands.append("right")
        if not pitches:
            raise ValueError("empty scale beat")
        groups.append({"pitches": pitches, "hands": hands})

    def phase(identifier: str, label: str, points: list[tuple[int | None, int | None]]) -> None:
        start = len(groups)
        for low, high in points:
            append(low, high)
        phases.append({"id": identifier, "label": label, "start": start, "end": len(groups)})

    phase("parallel-up", "Both hands ascend together one octave",
          [(i, i) for i in range(8)])
    phase("left-reverses-right-extends",
          "LH descends while RH ascends another octave, then RH returns while LH rests",
          [(7-i, 7+i) for i in range(1, 8)] +
          [(None, 14-i) for i in range(1, 8)])
    phase("parallel-up-return", "Both hands ascend one octave and return",
          [(i, 7+i) for i in range(1, 8)] +
          [(7-i, 14-i) for i in range(1, 8)])
    phase("contrary-out-return", "LH descends while RH ascends; both return",
          [(-i, 7+i) for i in range(1, 8)] +
          [(-7+i, 14-i) for i in range(1, 8)])
    phase("parallel-down", "Both hands descend one octave",
          [(-i, 7-i) for i in range(1, 8)])

    return {
        "contract_version": "onset-groups/v1",
        "onsets": groups,
        "phases": phases,
        "finger_cues": [
            {"onset_index": 5, "hand": "left", "finger": 3,
             "label": "LH first-octave crossing; review with teacher"},
            {"onset_index": 26, "hand": "left", "finger": 3,
             "label": "LH crossing while repeating upward scale"}
        ]
    }
