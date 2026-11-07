"""Conservative USB-MIDI trace diagnostics; physical hardware never self-attested."""
from __future__ import annotations

from collections import Counter


def inspect(take: dict) -> dict:
    if not isinstance(take, dict) or take.get("contract_version") != "midi-take/v1":
        raise ValueError("hardware inspect requires midi-take/v1")
    events = take.get("events")
    if not isinstance(events, list) or len(events) > 100000:
        raise ValueError("invalid MIDI event array")
    held = set()
    faults = []
    counts = Counter()
    channels = set()
    pitches = set()
    prev_time = -1
    for event in events:
        if not isinstance(event, dict):
            raise ValueError("invalid MIDI event")
        t = event.get("t_ms")
        ch = event.get("channel")
        if type(t) is not int or t < 0 or t < prev_time or type(ch) is not int or not 0 <= ch <= 15:
            raise ValueError("invalid MIDI event time/channel")
        prev_time = t
        channels.add(ch)
        kind = event.get("type")
        if kind == "control_change":
            if event.get("control") != 64 or type(event.get("value")) is not int or not 0 <= event["value"] <= 127:
                raise ValueError("unsupported MIDI control event")
            counts["cc64_on" if event["value"] >= 64 else "cc64_off"] += 1
            continue
        if kind not in ("note_on", "note_off"):
            raise ValueError("unsupported MIDI event kind")
        note = event.get("note")
        vel = event.get("velocity")
        if type(note) is not int or not 0 <= note <= 127 or type(vel) is not int or not 0 <= vel <= 127:
            raise ValueError("invalid note/velocity")
        key = (ch, note)
        if kind == "note_on" and vel > 0:
            counts["note_on"] += 1
            pitches.add(note)
            if key in held:
                faults.append("duplicate-note-on")
            held.add(key)
        else:
            counts["note_off"] += 1
            if key not in held:
                faults.append("unmatched-note-off")
            else:
                held.remove(key)
    if held:
        faults.append("unreleased-note")
    return {
        "record_type": "midi-trace-inspection",
        "version": "1",
        "event_count": len(events),
        "counts": {k: counts[k] for k in
                   ("note_on", "note_off", "cc64_on", "cc64_off")},
        "midi_channels": sorted(channels),
        "observed_pitches": sorted(pitches),
        "trace_integrity": "pass" if not faults and counts["note_on"] else
                           "fail" if faults else "unknown",
        "faults": sorted(set(faults)),
        "physical_device_qualified": False,
        "qualification_limits": [
            "MIDI events and port labels do not authenticate a physical device",
            "the connected remote environment may not expose host ALSA USB MIDI",
            "verify the actual Oxygen Pro 61 using the on-device checklist"
        ],
    }
