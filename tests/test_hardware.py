"""Trace-only qualification tests. These are not physical-device tests."""
import json
from pathlib import Path
import unittest

from piano_practice.hardware import inspect

ROOT = Path(__file__).resolve().parents[1]


class HardwareTraceTests(unittest.TestCase):
    def setUp(self):
        self.take = json.loads(
            (ROOT / "examples/midi-takes/pulse-quarter-pass.json").read_text(encoding="utf-8")
        )

    def test_synthetic_notes_have_integrity_without_physical_attestation(self):
        result = inspect(self.take)
        self.assertEqual(result["trace_integrity"], "pass")
        self.assertEqual(result["counts"]["note_on"], 4)
        self.assertEqual(result["counts"]["note_off"], 4)
        self.assertEqual(result["observed_pitches"], [60])
        self.assertFalse(result["physical_device_qualified"])

    def test_cc64_pedal_on_off_preserved(self):
        self.take["events"].extend([
            dict(t_ms=3400, type="control_change", channel=0, control=64, value=127),
            dict(t_ms=3500, type="control_change", channel=0, control=64, value=0)
        ])
        result = inspect(self.take)
        self.assertEqual(result["counts"]["cc64_on"], 1)
        self.assertEqual(result["counts"]["cc64_off"], 1)
        self.assertEqual(result["trace_integrity"], "pass")

    def test_unreleased_note_fails(self):
        self.take["events"].pop()
        self.assertEqual(inspect(self.take)["trace_integrity"], "fail")
        self.assertIn("unreleased-note", inspect(self.take)["faults"])

    def test_zero_velocity_note_on_is_release(self):
        for event in self.take["events"]:
            if event["type"] == "note_off":
                event["type"] = "note_on"
        self.assertEqual(inspect(self.take)["trace_integrity"], "pass")

    def test_invalid_timestamp_or_control_rejected(self):
        self.take["events"][0]["t_ms"] = -1
        with self.assertRaises(ValueError):
            inspect(self.take)
        self.take["events"][0]["t_ms"] = 0
        self.take["events"].append(
            dict(t_ms=4000, type="control_change", channel=0, control=1, value=127)
        )
        with self.assertRaises(ValueError):
            inspect(self.take)

    def test_empty_trace_is_unknown_not_qualified(self):
        self.take["events"] = []
        result = inspect(self.take)
        self.assertEqual(result["trace_integrity"], "unknown")
        self.assertFalse(result["physical_device_qualified"])


if __name__ == "__main__":
    unittest.main()
