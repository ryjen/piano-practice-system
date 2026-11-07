"""Onset groups are the shared MIDI and MusicXML realization contract."""
import copy
import json
from pathlib import Path
import unittest
import xml.etree.ElementTree as ET

from piano_practice.core import propose, validate_catalog
from piano_practice.midi import assess
from piano_practice.piango import to_piango_musicxml
from piano_practice.timeline import onset_groups

ROOT = Path(__file__).resolve().parents[1]


class OnsetGroupTests(unittest.TestCase):
    def setUp(self):
        self.catalog = json.loads((ROOT / "catalogs/exercises.json").read_text())
        validate_catalog(self.catalog)

    def take(self, *, spread=0, swap_pair=False, missing=False, extra=False,
             tempo=50):
        events = []
        pairs = [(48, 60), (52, 64), (55, 67), (48, 60)]
        for beat, pair in enumerate(pairs):
            notes = pair[::-1] if swap_pair else pair
            for position, pitch in enumerate(notes):
                if missing and beat == 2 and position == 1:
                    continue
                start = beat * 1200 + position * spread
                events.append(dict(t_ms=start, type="note_on",
                                   channel=0, note=pitch, velocity=70))
                events.append(dict(t_ms=start + 200, type="note_off",
                                   channel=0, note=pitch, velocity=0))
        if extra:
            events.extend([
                dict(t_ms=4000, type="note_on", channel=0, note=81, velocity=50),
                dict(t_ms=4200, type="note_off", channel=0, note=81, velocity=0)
            ])
        events.sort(key=lambda e: e["t_ms"])
        return dict(contract_version="midi-take/v1",
                    exercise_id="coordination-together",
                    bpm=tempo, events=events)

    def test_session_proposal_carries_normalized_realization(self):
        state = json.loads((ROOT / "examples/learner-state.json").read_text())
        config = json.loads((ROOT / "config/practice.json").read_text())
        session = propose(self.catalog, state, config, "2026-11-10")
        self.assertEqual(session["realization"]["contract_version"], "onset-groups/v1")
        self.assertEqual(len(session["realization"]["onsets"]), len(session["notes_midi"]))

    def test_exact_simultaneous_octave_pairs_pass_advisory_checks(self):
        result = assess(self.take(), self.catalog)
        self.assertEqual(result["checks"]["pitch_sequence"], "pass")
        self.assertEqual(result["checks"]["inter_onset_intervals"], "pass")
        self.assertEqual(result["checks"]["within_group_sync"], "pass")
        self.assertEqual(result["checks"]["required_human_observation"], "unknown")
        self.assertFalse(result["pass"])

    def test_within_pair_transport_order_is_irrelevant(self):
        result = assess(self.take(swap_pair=True), self.catalog)
        self.assertEqual(result["checks"]["pitch_sequence"], "pass")
        self.assertEqual(result["checks"]["within_group_sync"], "pass")

    def test_staggered_hands_fail_sync_even_when_group_timing_is_regular(self):
        result = assess(self.take(spread=130), self.catalog)
        self.assertEqual(result["checks"]["inter_onset_intervals"], "pass")
        self.assertEqual(result["checks"]["within_group_sync"], "fail")
        self.assertEqual(result["max_within_group_spread_ms"], 130)

    def test_missing_and_extra_notes_cannot_match_groups(self):
        for key in ("missing", "extra"):
            with self.subTest(key=key):
                result = assess(self.take(**{key: True}), self.catalog)
                self.assertEqual(result["checks"]["pitch_sequence"], "fail")
                self.assertFalse(result["pass"])

    def test_sequential_drills_keep_legacy_behavior(self):
        data = json.loads((ROOT / "examples/midi-takes/pulse-quarter-pass.json").read_text())
        result = assess(data, self.catalog)
        self.assertEqual(result["checks"]["within_group_sync"], "not-applicable")
        self.assertTrue(result["pass"])

    def test_invalid_realization_does_not_pass_catalog_admission(self):
        for scenario in ("missing-note", "same-hand", "bad-version", "bad-pitch"):
            with self.subTest(scenario=scenario):
                catalog = copy.deepcopy(self.catalog)
                ex = next(x for x in catalog["exercises"] if x["id"] == "coordination-together")
                onsets = ex["realization"]["onsets"]
                if scenario == "missing-note":
                    onsets.pop()
                elif scenario == "same-hand":
                    onsets[0]["hands"] = ["left", "left"]
                elif scenario == "bad-version":
                    ex["realization"]["contract_version"] = "onset-groups/v999"
                elif scenario == "bad-pitch":
                    onsets[0]["pitches"][0] = 100
                with self.assertRaises(ValueError):
                    validate_catalog(catalog)

    def test_musicxml_and_midi_derive_from_same_groups(self):
        for ident in ("coordination-alternating", "coordination-together"):
            with self.subTest(exercise=ident):
                ex = next(x for x in self.catalog["exercises"] if x["id"] == ident)
                groups = onset_groups(ex)
                xml = ET.fromstring(to_piango_musicxml(self.catalog, ident))
                parts = xml.findall("./part")
                self.assertEqual(len(parts), 2)
                for i, group in enumerate(groups):
                    # Extract precisely the two intended part events at each beat.
                    part_events = []
                    for p in parts:
                        notes = p.findall("./measure/note")
                        note = notes[i]
                        part_events.append(note.find("pitch") is not None)
                    self.assertEqual(sum(part_events), len(group["pitches"]))


if __name__ == "__main__":
    unittest.main()
