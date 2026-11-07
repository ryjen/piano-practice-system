"""Versioned, explicit onset groups for reference exercises.

Flat MIDI pitch lists are retained for legacy consumers. A realization states
which pitches are intended to begin together and which hand is *intended*,
not which finger or hand was actually used.
"""
from __future__ import annotations

VERSION = "onset-groups/v1"


def onset_groups(exercise: dict) -> list[dict]:
    notes = exercise["notes"]
    realization = exercise.get("realization")
    if realization is None:
        return [{"pitches": [pitch], "hands": [None]} for pitch in notes]
    required = {"contract_version", "onsets"}
    optional = {"phases", "finger_cues"}
    if (not isinstance(realization, dict)
            or not required <= set(realization)
            or not set(realization) <= (required | optional)
            or realization["contract_version"] != VERSION):
        raise ValueError("unsupported exercise realization contract")
    raw = realization["onsets"]
    if not isinstance(raw, list) or not 1 <= len(raw) <= 128:
        raise ValueError("invalid onset-group list")
    groups = []
    for group in raw:
        if not isinstance(group, dict) or set(group) != {"pitches", "hands"}:
            raise ValueError("invalid onset-group fields")
        pitches = group["pitches"]
        hands = group["hands"]
        if (not isinstance(pitches, list) or not 1 <= len(pitches) <= 2
                or not isinstance(hands, list) or len(hands) != len(pitches)):
            raise ValueError("invalid onset-group size")
        if any(type(n) is not int or not 0 <= n <= 127 for n in pitches):
            raise ValueError("invalid onset-group pitch")
        if any(h not in ("left", "right") for h in hands):
            raise ValueError("explicit realization needs named intended hands")
        if len(set(hands)) != len(hands):
            raise ValueError("two notes cannot both claim the same intended hand")
        groups.append({"pitches": list(pitches), "hands": list(hands)})
    if [p for group in groups for p in group["pitches"]] != notes:
        raise ValueError("onset-group pitch order does not match legacy notes")
    phases = realization.get("phases", [])
    if not isinstance(phases, list) or len(phases) > 16:
        raise ValueError("invalid exercise phases")
    if phases:
        cursor = 0
        ids = set()
        for phase in phases:
            if (not isinstance(phase, dict) or set(phase) !=
                    {"id", "label", "start", "end"}):
                raise ValueError("invalid phase fields")
            if (not isinstance(phase["id"], str) or not phase["id"]
                    or phase["id"] in ids or
                    not isinstance(phase["label"], str) or not phase["label"]
                    or type(phase["start"]) is not int or type(phase["end"]) is not int
                    or phase["start"] != cursor or
                    not cursor < phase["end"] <= len(groups)):
                raise ValueError("invalid or noncontiguous phase")
            ids.add(phase["id"])
            cursor = phase["end"]
        if cursor != len(groups):
            raise ValueError("exercise phases do not cover all onsets")
    cues = realization.get("finger_cues", [])
    if not isinstance(cues, list) or len(cues) > 32:
        raise ValueError("invalid fingering cues")
    seen_cues = set()
    for cue in cues:
        if (not isinstance(cue, dict) or set(cue) !=
                {"onset_index", "hand", "finger", "label"}):
            raise ValueError("invalid fingering cue fields")
        ix = cue["onset_index"]
        hand = cue["hand"]
        if (type(ix) is not int or not 0 <= ix < len(groups)
                or hand not in ("left", "right")
                or hand not in groups[ix]["hands"]
                or type(cue["finger"]) is not int or not 1 <= cue["finger"] <= 5
                or not isinstance(cue["label"], str) or not cue["label"]
                or (ix, hand) in seen_cues):
            raise ValueError("invalid or duplicate fingering cue")
        seen_cues.add((ix, hand))
    return groups
