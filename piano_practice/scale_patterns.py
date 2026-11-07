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
    """Provisional C-major realization of the player's five-phase motion.

    The relative positions are explicit and continuous. Phase 2 and phase 4
    each descend with LH and ascend with RH, then BOTH hands reverse and
    return. Phase 3 ascends and returns in parallel from the end of phase 2.
    The C3/C4 starting registers are illustrative, not player-confirmed.
    Finger crossings belong to a separate two-octave reference exercise.
    """
    groups: list[dict] = []
    phases: list[dict] = []

    def append(lh_degree: int, rh_degree: int) -> None:
        groups.append({
            "pitches": [c_major(48, lh_degree), c_major(60, rh_degree)],
            "hands": ["left", "right"],
        })

    def phase(identifier: str, label: str,
              points: list[tuple[int, int]]) -> None:
        start = len(groups)
        for low, high in points:
            append(low, high)
        phases.append({
            "id": identifier, "label": label,
            "start": start, "end": len(groups),
        })

    # After phase 1: LH C4 / RH C5. A contrary-motion excursion goes
    # LH C4→C3 and RH C5→C6, then BOTH reverse back to C4/C5.
    contrary_out_return = (
        [(7 - i, 7 + i) for i in range(1, 8)]
        + [(i, 14 - i) for i in range(1, 8)]
    )
    phase("parallel-up", "Both hands ascend together one octave",
          [(i, i) for i in range(8)])
    phase("left-reverses-right-extends",
          "LH descends and RH ascends one octave in contrary motion; both return",
          contrary_out_return)
    phase("parallel-up-return", "Both hands ascend one octave and return",
          [(7 + i, 7 + i) for i in range(1, 8)]
          + [(14 - i, 14 - i) for i in range(1, 8)])
    phase("contrary-out-return",
          "LH descends and RH ascends one octave in contrary motion; both return",
          contrary_out_return)
    phase("parallel-down", "Both hands descend one octave",
          [(7 - i, 7 - i) for i in range(1, 8)])

    return {
        "contract_version": "onset-groups/v1",
        "onsets": groups,
        "phases": phases,
        # The LH 3→4 crossing cues belong to the separate two-octave drill.
        # Exact five-phase fingering has not been established.
        "finger_cues": [],
    }
