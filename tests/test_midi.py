import copy
import json
import unittest
from pathlib import Path

from piano_practice.midi import assess

ROOT = Path(__file__).resolve().parents[1]


def load(p):
    return json.loads((ROOT / p).read_text(encoding="utf-8"))


class MidiAssessmentTests(unittest.TestCase):
    def setUp(self):
        self.catalog = load("catalogs/exercises.json")
        self.take = load("examples/midi-takes/pulse-quarter-pass.json")

    def test_synthetic_steady_pulse_passes(self):
        r = assess(self.take, self.catalog)
        self.assertTrue(r["pass"])
        self.assertEqual(r["checks"]["note_lifecycle"], "pass")
        self.assertEqual(r["checks"]["relative_dynamics"], "not-applicable")
        self.assertEqual(r["max_interval_deviation_ms"], 0)

    def test_extra_note_fails_pitch_and_lifecycle(self):
        self.take["events"].insert(1, {
            "t_ms": 100, "type": "note_on", "channel": 0, "note": 67, "velocity": 70
        })
        r = assess(self.take, self.catalog)
        self.assertFalse(r["pass"])
        self.assertEqual(r["checks"]["pitch_sequence"], "fail")
        self.assertEqual(r["checks"]["note_lifecycle"], "fail")

    def test_unreleased_note_fails(self):
        self.take["events"].pop()
        self.assertEqual(assess(self.take, self.catalog)["checks"]["note_lifecycle"], "fail")

    def test_midi_zero_velocity_note_on_is_release(self):
        for event in self.take["events"]:
            if event["type"] == "note_off":
                event["type"] = "note_on"
        self.assertTrue(assess(self.take, self.catalog)["pass"])

    def test_timing_outside_gate_fails(self):
        for event in self.take["events"]:
            if event["t_ms"] in (1000, 1400):
                event["t_ms"] += 250
        self.take["events"].sort(key=lambda e: e["t_ms"])
        self.assertEqual(assess(self.take, self.catalog)["checks"]["inter_onset_intervals"], "fail")

    def test_declared_tempo_is_used_for_a_slowed_practice_take(self):
        for event in self.take["events"]:
            event["t_ms"] = int(event["t_ms"] * 1.5)
        self.assertFalse(assess(self.take, self.catalog)["pass"])
        self.take["bpm"] = 40
        result = assess(self.take, self.catalog)
        self.assertTrue(result["pass"])
        self.assertEqual(result["declared_bpm"], 40)

    def test_high_tempo_collapsed_attacks_fail_timing(self):
        take = copy.deepcopy(self.take)
        take["exercise_id"] = "pulse-eighth"
        take["bpm"] = 180
        take["events"] = []
        for _ in range(8):
            take["events"].extend([
                dict(t_ms=0, type="note_on", note=60, channel=0, velocity=70),
                dict(t_ms=0, type="note_off", note=60, channel=0, velocity=0),
            ])
        result = assess(take, self.catalog)
        self.assertEqual(result["checks"]["pitch_sequence"], "pass")
        self.assertEqual(result["checks"]["note_lifecycle"], "pass")
        self.assertEqual(result["checks"]["inter_onset_intervals"], "fail")
        self.assertFalse(result["pass"])
        self.assertLess(result["timing_tolerance_ms"], result["target_interval_ms"])

    def test_high_tempo_even_notes_pass_timing(self):
        take = copy.deepcopy(self.take)
        take["exercise_id"] = "pulse-eighth"
        take["bpm"] = 180
        take["events"] = []
        for i in range(8):
            start = round(i * (60000 / 180 / 2))
            take["events"].extend([
                dict(t_ms=start, type="note_on", note=60, channel=0, velocity=70),
                dict(t_ms=start+50, type="note_off", note=60, channel=0, velocity=0),
            ])
        self.assertTrue(assess(take, self.catalog)["pass"])

    def test_alternating_dynamics_rejects_crescendo(self):
        take = copy.deepcopy(self.take)
        take["exercise_id"] = "dynamics-contrast"
        take["events"] = []
        for i, velocity in enumerate([10, 22, 34, 46, 58, 70]):
            take["events"].extend([
                dict(t_ms=i*1000, type="note_on", note=60, channel=0, velocity=velocity),
                dict(t_ms=i*1000+350, type="note_off", note=60, channel=0, velocity=0),
            ])
        result = assess(take, self.catalog)
        self.assertEqual(result["checks"]["relative_dynamics"], "fail")
        self.assertFalse(result["pass"])

    def test_wrong_note_fails(self):
        self.take["events"][0]["note"] = 61
        self.take["events"][1]["note"] = 61
        self.assertEqual(assess(self.take, self.catalog)["checks"]["pitch_sequence"], "fail")

    def test_relative_velocity_contrast(self):
        take = copy.deepcopy(self.take)
        take["exercise_id"] = "dynamics-contrast"
        take["events"] = []
        for i in range(6):
            v = 45 if i % 2 == 0 else 75
            take["events"].extend([
                dict(t_ms=i*1000, type="note_on", note=60, channel=0, velocity=v),
                dict(t_ms=i*1000+350, type="note_off", note=60, channel=0, velocity=0),
            ])
        self.assertTrue(assess(take, self.catalog)["pass"])
        for ev in take["events"]:
            if ev["type"] == "note_on":
                ev["velocity"] = 60
        self.assertEqual(assess(take, self.catalog)["checks"]["relative_dynamics"], "fail")

    def test_unsorted_events_are_rejected(self):
        self.take["events"][0], self.take["events"][1] = (
            self.take["events"][1], self.take["events"][0]
        )
        with self.assertRaises(ValueError):
            assess(self.take, self.catalog)

    def test_invalid_schema_is_rejected(self):
        self.take["contract_version"] = "midi-take/v99"
        with self.assertRaises(ValueError):
            assess(self.take, self.catalog)


if __name__ == "__main__":
    unittest.main()
