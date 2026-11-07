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
    if (not isinstance(realization, dict)
            or set(realization) != {"contract_version", "onsets"}
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
    return groups
