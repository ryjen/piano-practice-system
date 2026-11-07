"""Deterministic assessment of *key MIDI events*, not physical technique."""
from __future__ import annotations

from collections import Counter

from .core import validate_catalog
from .timeline import onset_groups


def assess(take: dict, catalog: dict) -> dict:
    validate_catalog(catalog)
    if take.get("contract_version") != "midi-take/v1":
        raise ValueError("unsupported take contract")
    exercises = {e["id"]: e for e in catalog["exercises"]}
    exercise_id = take.get("exercise_id")
    if exercise_id not in exercises:
        raise ValueError("unknown exercise")
    ex = exercises[exercise_id]
    events = take.get("events")
    if not isinstance(events, list) or len(events) > 100000:
        raise ValueError("invalid MIDI events")
    active = set()
    onsets = []
    errors = []
    last_time = -1
    for ev in events:
        if (not isinstance(ev, dict) or type(ev.get("t_ms")) is not int
                or ev["t_ms"] < 0 or ev["t_ms"] < last_time):
            raise ValueError("events require nondecreasing integer t_ms")
        last_time = ev["t_ms"]
        kind = ev.get("type")
        if kind not in ("note_on", "note_off", "control_change"):
            raise ValueError("unsupported MIDI event type")
        if type(ev.get("channel")) is not int or not 0 <= ev["channel"] <= 15:
            raise ValueError("invalid MIDI channel")
        if kind == "control_change":
            if ev.get("control") != 64 or type(ev.get("value")) is not int or not 0 <= ev["value"] <= 127:
                raise ValueError("only sustain pedal CC64 is admitted")
            continue
        if type(ev.get("note")) is not int or not 0 <= ev["note"] <= 127:
            raise ValueError("invalid note number")
        if type(ev.get("velocity")) is not int or not 0 <= ev["velocity"] <= 127:
            raise ValueError("invalid velocity")
        key = (ev["channel"], ev["note"])
        note_on = kind == "note_on" and ev["velocity"] > 0
        if note_on:
            if key in active:
                errors.append("overlapping_note_on")
            active.add(key)
            onsets.append(ev)
        else:
            if key not in active:
                errors.append("unpaired_note_off")
            else:
                active.remove(key)
    if active:
        errors.append("unreleased_notes")
    groups = onset_groups(ex)
    expected = ex["notes"]
    # Match each expected onset group as a multiset: a nearly simultaneous
    # RH/LH pair may arrive in either transport order. Single-note groups
    # preserve the legacy sequential pitch assessment.
    observed_groups = []
    cursor = 0
    pitch_match = len(onsets) == len(expected)
    for group in groups:
        span = len(group["pitches"])
        observed = onsets[cursor:cursor + span]
        cursor += span
        observed_groups.append(observed)
        if Counter(n["note"] for n in observed) != Counter(group["pitches"]):
            pitch_match = False
    pitches = "pass" if pitch_match else "fail"
    declared_bpm = take.get("bpm", ex["bpm"])
    if type(declared_bpm) is not int or not 40 <= declared_bpm <= 180:
        raise ValueError("declared bpm must be an integer from 40 to 180")
    target_interval = 60000.0 / declared_bpm / ex["subdivision"]
    all_group_notes_present = all(len(actual) == len(group["pitches"])
                                  for actual, group in zip(observed_groups, groups))
    group_starts = [min(n["t_ms"] for n in group)
                    for group in observed_groups if group]
    gaps = [group_starts[i+1] - group_starts[i]
            for i in range(len(group_starts)-1)]
    deviation = max((abs(g - target_interval) for g in gaps), default=None)
    timing_tolerance_ms = min(120.0, target_interval * 0.25)
    timing = "unknown" if not all_group_notes_present or len(group_starts) != len(groups) else (
        "pass" if deviation is not None and deviation <= timing_tolerance_ms else "fail"
    )
    polyphonic = any(len(group["pitches"]) > 1 for group in groups)
    synchronization_tolerance_ms = min(80.0, target_interval * 0.1)
    spreads = [max(n["t_ms"] for n in actual) - min(n["t_ms"] for n in actual)
               for actual in observed_groups if len(actual) > 1]
    synchronization = "not-applicable" if not polyphonic else (
        "unknown" if not all_group_notes_present else
        "pass" if all(spread <= synchronization_tolerance_ms for spread in spreads)
        else "fail"
    )
    lifecycle = "pass" if not errors else "fail"
    dynamics = "not-applicable"
    if ex.get("dynamics") == "alternate":
        if len(onsets) != len(expected):
            dynamics = "unknown"
        else:
            values = [e["velocity"] for e in onsets]
            # Verify both alternating edges; a simple crescendo must not pass.
            rises = all(values[i+1] - values[i] >= 12
                        for i in range(0, len(values)-1, 2))
            falls = all(values[i] - values[i+1] >= 12
                        for i in range(1, len(values)-1, 2))
            dynamics = "pass" if rises and falls else "fail"
    checks = {
        "pitch_sequence": pitches,
        "inter_onset_intervals": timing,
        "within_group_sync": synchronization,
        "note_lifecycle": lifecycle,
        "relative_dynamics": dynamics,
    }
    if ex.get("assessment_mode") == "human":
        checks["required_human_observation"] = "unknown"
    return {
        "record_type": "midi-assessment",
        "contract_version": "assessment/v1",
        "exercise_id": exercise_id,
        "checks": checks,
        "pass": all(v in ("pass", "not-applicable") for v in checks.values()),
        "expected_note_count": len(expected),
        "observed_note_count": len(onsets),
        "declared_bpm": declared_bpm,
        "target_interval_ms": round(target_interval, 3),
        "timing_tolerance_ms": round(timing_tolerance_ms, 3),
        "synchronization_tolerance_ms": round(synchronization_tolerance_ms, 3),
        "max_within_group_spread_ms": max(spreads, default=None),
        "max_interval_deviation_ms": None if deviation is None else round(deviation, 3),
        "lifecycle_errors": sorted(set(errors)),
        "limitations": [
            "tempo is declared by the player or catalog, not independently verified",
            "relative timing only; no proof of click-phase alignment",
            "MIDI note events do not verify which hand or finger played",
            "comfort and listening quality require explicit human observation",
            "this assessment is advisory evidence, not mastery promotion"
        ],
    }
