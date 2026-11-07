"""Deterministic assessment of *key MIDI events*, not physical technique."""
from __future__ import annotations

from .core import validate_catalog


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
        if not isinstance(ev, dict) or type(ev.get("t_ms")) is not int or ev["t_ms"] < last_time:
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
    played = [ev["note"] for ev in onsets]
    expected = ex["notes"]
    pitches = "pass" if played == expected else "fail"
    target_interval = 60000.0 / ex["bpm"] / ex["subdivision"]
    gaps = [onsets[i+1]["t_ms"] - onsets[i]["t_ms"] for i in range(len(onsets)-1)]
    deviation = max((abs(g - target_interval) for g in gaps), default=None)
    timing = "unknown" if len(gaps) != len(expected)-1 else (
        "pass" if deviation is not None and deviation <= 180 else "fail"
    )
    lifecycle = "pass" if not errors else "fail"
    dynamics = "not-applicable"
    if ex.get("dynamics") == "alternate":
        if len(onsets) != len(expected):
            dynamics = "unknown"
        else:
            values = [e["velocity"] for e in onsets]
            dynamics = "pass" if all(
                values[i+1] >= values[i] + 12 for i in range(0, len(values)-1, 2)
            ) else "fail"
    checks = {
        "pitch_sequence": pitches,
        "inter_onset_intervals": timing,
        "note_lifecycle": lifecycle,
        "relative_dynamics": dynamics,
    }
    return {
        "record_type": "midi-assessment",
        "contract_version": "assessment/v1",
        "exercise_id": exercise_id,
        "checks": checks,
        "pass": all(v in ("pass", "not-applicable") for v in checks.values()),
        "expected_note_count": len(expected),
        "observed_note_count": len(onsets),
        "target_interval_ms": round(target_interval, 3),
        "max_interval_deviation_ms": None if deviation is None else round(deviation, 3),
        "lifecycle_errors": sorted(set(errors)),
        "limitations": [
            "relative timing only; no proof of click-phase alignment",
            "MIDI note events do not verify which hand or finger played",
            "comfort and listening quality require explicit human observation",
            "this assessment is advisory evidence, not mastery promotion"
        ],
    }
