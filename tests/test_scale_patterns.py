"""Original arpeggio and personalized two-hand scale references."""
import copy
import json
from pathlib import Path
import unittest
import xml.etree.ElementTree as ET

from piano_practice.core import validate_catalog
from piano_practice.midi import assess
from piano_practice.piango import to_piango_musicxml
from piano_practice.scale_patterns import c_major, hands_together_two_octaves, five_phase_opposing_scales
from piano_practice.timeline import onset_groups

ROOT = Path(__file__).resolve().parents[1]


class PersonalScalePatternsTests(unittest.TestCase):
    def setUp(self):
        self.catalog = json.loads((ROOT / "catalogs/exercises.json").read_text())
        self.exercises = {e["id"]: e for e in self.catalog["exercises"]}
        validate_catalog(self.catalog)

    def test_two_octave_left_hand_crossings_at_first_three_then_four(self):
        pattern = self.exercises["scale-crossings-two-octaves"]
        self.assertEqual(pattern["realization"], hands_together_two_octaves())
        groups = onset_groups(pattern)
        self.assertEqual(len(groups), 15)
        self.assertEqual(groups[0]["pitches"], [48, 60])
        self.assertEqual(groups[7]["pitches"], [60, 72])
        self.assertEqual(groups[14]["pitches"], [72, 84])
        cues = pattern["realization"]["finger_cues"]
        self.assertEqual([(c["onset_index"], c["finger"], c["hand"]) for c in cues],
                         [(5, 3, "left"), (8, 4, "left")])
        self.assertEqual(groups[5]["pitches"][0], 57)  # A3
        self.assertEqual(groups[8]["pitches"][0], 62)  # D4
        root = ET.fromstring(to_piango_musicxml(
            self.catalog, pattern["id"], fingering_reference=True
        ))
        self.assertEqual(root.findall("./part")[0].findall(".//fingering"), [])
        self.assertEqual([int(x.text) for x in root.findall("./part")[1].findall(".//fingering")],
                         [3, 4])
        plain = ET.fromstring(to_piango_musicxml(self.catalog, pattern["id"]))
        self.assertEqual(len(plain.findall(".//fingering")), 0)

    def test_five_phases_cover_groups_without_ambiguous_timeline(self):
        ex = self.exercises["scale-five-phase-opposing"]
        realization = ex["realization"]
        self.assertEqual(realization, five_phase_opposing_scales())
        groups = onset_groups(ex)
        self.assertEqual(len(groups), 57)
        phases = realization["phases"]
        self.assertEqual([p["id"] for p in phases], [
            "parallel-up", "left-reverses-right-extends", "parallel-up-return",
            "contrary-out-return", "parallel-down"
        ])
        self.assertEqual([(p["start"], p["end"]) for p in phases],
                         [(0, 8), (8, 22), (22, 36), (36, 50), (50, 57)])
        # All five phases are played with BOTH hands, including the return
        # in phase 2 and phase 4. Check concrete pitches and phase continuity.
        self.assertTrue(all(g["hands"] == ["left", "right"] for g in groups))
        self.assertEqual(groups[0]["pitches"], [48, 60])     # LH C3 / RH C4
        self.assertEqual(groups[7]["pitches"], [60, 72])    # phase 1 end
        self.assertEqual(groups[14]["pitches"], [48, 84])   # phase 2 outer notes
        self.assertEqual(groups[15]["pitches"], [50, 83])   # BOTH reverse
        self.assertEqual(groups[21]["pitches"], [60, 72])   # phase 2 return
        self.assertEqual(groups[28]["pitches"], [72, 84])   # phase 3 apex
        self.assertEqual(groups[35]["pitches"], [60, 72])   # phase 3 return
        self.assertEqual(groups[42]["pitches"], [48, 84])   # phase 4 outer notes
        self.assertEqual(groups[49]["pitches"], [60, 72])   # phase 4 return
        self.assertEqual(groups[56]["pitches"], [48, 60])   # final lower C3/C4
        self.assertEqual(groups[8:22], groups[36:50])       # same contrary arc
        self.assertEqual(realization["finger_cues"], [])     # not confirmed here
        for before, after in zip(groups, groups[1:]):
            self.assertTrue(all(1 <= abs(b - a) <= 2 for a, b in
                                zip(before["pitches"], after["pitches"])))
        root = ET.fromstring(to_piango_musicxml(self.catalog, ex["id"],
                                                fingering_reference=True))
        self.assertEqual(len(root.findall("./part")), 2)
        self.assertEqual(len(root.findall(".//direction-type/words")), 5)
        self.assertEqual(root.findall(".//fingering"), [])
        for part in root.findall("./part"):
            rendered = part.findall("./measure/note")
            # Three trailing rests merely fill the last four-beat measure;
            # every one of the 57 authored hand onsets must remain a note.
            self.assertTrue(all(n.find("pitch") is not None for n in rendered[:57]))
            self.assertTrue(all(n.find("rest") is not None for n in rendered[57:]))


    def test_five_phase_direction_and_both_hand_reversals(self):
        """Direction is an independent musical assertion, not a generator echo."""
        groups = onset_groups(self.exercises["scale-five-phase-opposing"])

        def motion(start, end, left_sign, right_sign):
            for i in range(start, end):
                before = groups[i - 1]["pitches"]
                after = groups[i]["pitches"]
                self.assertEqual(
                    (1 if after[0] > before[0] else -1,
                     1 if after[1] > before[1] else -1),
                    (left_sign, right_sign),
                    f"wrong direction at onset {i}"
                )

        motion(1, 8, +1, +1)    # phase 1: parallel ascent
        motion(8, 15, -1, +1)   # phase 2: outward contrary
        motion(15, 22, +1, -1)  # phase 2: BOTH return
        motion(22, 29, +1, +1)  # phase 3: parallel ascent
        motion(29, 36, -1, -1)  # phase 3: BOTH return
        motion(36, 43, -1, +1)  # phase 4: outward contrary
        motion(43, 50, +1, -1)  # phase 4: BOTH return
        motion(50, 57, -1, -1)  # phase 5: parallel descent
        self.assertEqual(groups[0]["pitches"], groups[-1]["pitches"])

    def test_original_arpeggios_are_playable_sequences(self):
        foundation = self.exercises["arpeggio-major-one-octave"]
        advanced = self.exercises["arpeggio-major-minor-two-octaves"]
        self.assertEqual(foundation["notes"], [60, 64, 67, 72, 67, 64, 60])
        self.assertEqual(advanced["notes"][:7], [60, 64, 67, 72, 76, 79, 84])
        self.assertEqual(advanced["notes"][-7:], [81, 76, 72, 69, 64, 60, 57])
        self.assertEqual(foundation["assessment_mode"], "human")
        self.assertEqual(advanced["assessment_mode"], "human")
        for ident in (foundation["id"], advanced["id"]):
            root = ET.fromstring(to_piango_musicxml(self.catalog, ident))
            self.assertEqual(len(root.findall("./part")), 1)

    def test_midi_pair_timing_is_advisory_only_for_provisional_scale(self):
        ex = self.exercises["scale-crossings-two-octaves"]
        events = []
        for i, group in enumerate(onset_groups(ex)):
            for j, note in enumerate(group["pitches"]):
                time = i * 1200 + j * 5
                events.append({"t_ms": time, "type": "note_on", "channel": 0,
                               "note": note, "velocity": 70})
                events.append({"t_ms": time + 150, "type": "note_off",
                               "channel": 0, "note": note, "velocity": 0})
        events.sort(key=lambda x: x["t_ms"])
        result = assess(dict(contract_version="midi-take/v1", exercise_id=ex["id"],
                             bpm=50, events=events), self.catalog)
        self.assertEqual(result["checks"]["pitch_sequence"], "pass")
        self.assertEqual(result["checks"]["within_group_sync"], "pass")
        self.assertEqual(result["checks"]["inter_onset_intervals"], "pass")
        self.assertEqual(result["checks"]["required_human_observation"], "unknown")
        self.assertFalse(result["pass"])

    def test_malformed_phase_or_fingering_reference_fails_catalog_admission(self):
        for mode in ("phase-gap", "phase-overrun", "unknown-hand", "invalid-finger",
                     "wrong-fingering-position"):
            with self.subTest(mode=mode):
                catalog = copy.deepcopy(self.catalog)
                ex = next(x for x in catalog["exercises"]
                          if x["id"] == "scale-five-phase-opposing")
                pattern = ex["realization"]
                if mode == "phase-gap":
                    pattern["phases"][1]["start"] += 1
                if mode == "phase-overrun":
                    pattern["phases"][-1]["end"] += 1
                if mode in ("unknown-hand", "invalid-finger"):
                    crossing = next(x for x in catalog["exercises"]
                                    if x["id"] == "scale-crossings-two-octaves")
                    cue = crossing["realization"]["finger_cues"][0]
                    if mode == "unknown-hand":
                        cue["hand"] = "not-a-hand"
                    else:
                        cue["finger"] = 0
                if mode == "wrong-fingering-position":
                    alternating = next(x for x in catalog["exercises"]
                                       if x["id"] == "coordination-alternating")
                    alternating["realization"]["finger_cues"] = [{
                        "onset_index": 0, "hand": "right",
                        "finger": 3, "label": "invalid RH cue on LH-only note",
                    }]
                with self.assertRaises(ValueError):
                    validate_catalog(catalog)

    def test_signed_scale_degree_maps_to_c_major_correctly(self):
        self.assertEqual([c_major(48, i) for i in (-7, -6, -1, 0, 1, 6, 7)],
                         [36, 38, 47, 48, 50, 59, 60])


if __name__ == "__main__":
    unittest.main()
