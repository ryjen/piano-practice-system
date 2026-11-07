"""Contract-level tests for offline PianGo MusicXML exports."""
import copy
import json
import subprocess
import sys
import unittest
import xml.etree.ElementTree as ET
from pathlib import Path

from piano_practice.piango import STEPS, to_piango_musicxml
from piano_practice.timeline import onset_groups

ROOT = Path(__file__).resolve().parents[1]


def catalog():
    return json.loads((ROOT / "catalogs/exercises.json").read_text(encoding="utf-8"))


def pitch_numbers(part):
    pitches = []
    for note in part.findall("./measure/note"):
        p = note.find("pitch")
        if p is None:
            pitches.append(None)
        else:
            pitches.append(
                (int(p.findtext("octave")) + 1) * 12
                + STEPS[p.findtext("step")]
                + int(p.findtext("alter", "0"))
            )
    return pitches


class PianGoExportTests(unittest.TestCase):
    def test_every_catalog_exercise_renders_valid_score_without_mutation(self):
        source = catalog()
        snapshot = copy.deepcopy(source)
        for ex in source["exercises"]:
            with self.subTest(exercise=ex["id"]):
                score = to_piango_musicxml(source, ex["id"])
                root = ET.fromstring(score)
                self.assertEqual(root.tag, "score-partwise")
                self.assertEqual(root.attrib["version"], "4.0")
                self.assertEqual(root.findtext("./movement-title"), ex["title"])
                parts = root.findall("part")
                self.assertIn(len(parts), (1, 2))
                expected = ex["notes"]
                if ex["id"] == "coordination-alternating":
                    self.assertEqual(pitch_numbers(parts[0])[::2][:len(expected) // 2], [None] * 4)
                    self.assertEqual(pitch_numbers(parts[0])[1::2][:4], expected[1::2])
                    self.assertEqual(pitch_numbers(parts[1])[::2][:4], expected[::2])
                    self.assertEqual(pitch_numbers(parts[1])[1::2][:4], [None] * 4)
                elif ex.get("realization") is not None:
                    groups = onset_groups(ex)
                    for part_index, hand in enumerate(("right", "left")):
                        intended = [
                            next((note for note, role in zip(group["pitches"], group["hands"])
                                  if role == hand), None)
                            for group in groups
                        ]
                        self.assertEqual(pitch_numbers(parts[part_index])[:len(groups)], intended)
                    self.assertEqual(parts[0].findtext("./measure/attributes/clef/sign"), "G")
                    self.assertEqual(parts[1].findtext("./measure/attributes/clef/sign"), "F")
                else:
                    self.assertEqual(pitch_numbers(parts[0])[:len(expected)], expected)
                for part in parts:
                    for measure in part.findall("measure"):
                        durations = [int(n.findtext("duration")) for n in measure.findall("note")]
                        self.assertEqual(sum(durations), 8)
                self.assertEqual(len(root.findall(".//fingering")), 0)
        self.assertEqual(source, snapshot)

    def test_eighth_notes_are_not_exported_as_quarters(self):
        root = ET.fromstring(to_piango_musicxml(catalog(), "pulse-eighth"))
        notes = root.findall("./part/measure/note")
        self.assertEqual([n.findtext("type") for n in notes], ["eighth"] * 8)
        self.assertEqual([n.findtext("duration") for n in notes], ["1"] * 8)

    def test_preserves_authored_enharmonic_spelling(self):
        root = ET.fromstring(to_piango_musicxml(catalog(), "circle-fourths"))
        notes = root.findall("./part/measure/note")
        self.assertEqual(
            [(n.findtext("pitch/step"), n.findtext("pitch/alter")) for n in notes[:7]],
            [("C", None), ("F", None), ("B", "-1"), ("E", "-1"),
             ("A", "-1"), ("D", "-1"), ("G", "-1")],
        )

    def test_reference_fingerings_are_opt_in_not_performance_claims(self):
        root = ET.fromstring(to_piango_musicxml(
            catalog(), "minor-harmonic", fingering_reference=True
        ))
        self.assertEqual(
            [int(f.text) for f in root.findall(".//technical/fingering")],
            [1, 2, 3, 1, 2, 3, 4, 5],
        )
        other = ET.fromstring(to_piango_musicxml(
            catalog(), "circle-fifths", fingering_reference=True
        ))
        self.assertEqual(other.findall(".//technical/fingering"), [])

    def test_unknown_exercise_and_modified_spelling_fail_closed(self):
        with self.assertRaisesRegex(ValueError, "unknown exercise"):
            to_piango_musicxml(catalog(), "nonexistent")
        data = catalog()
        modified = next(e for e in data["exercises"] if e["id"] == "circle-fourths")
        modified["notes"][2] = 71
        with self.assertRaisesRegex(ValueError, "spelling disagrees"):
            to_piango_musicxml(data, "circle-fourths")

    def test_cli_produces_clean_xml_and_bad_id_fails(self):
        args = [
            sys.executable, "-m", "piano_practice.cli",
            "export", "--target", "piango", "--exercise", "reading-staff-steps",
            "--fingering-reference",
        ]
        ok = subprocess.run(args, cwd=ROOT, capture_output=True, text=True, check=False)
        self.assertEqual(ok.returncode, 0, ok.stderr)
        self.assertEqual(len(ET.fromstring(ok.stdout).findall(".//fingering")), 5)
        bad = subprocess.run(
            args[:7] + ["does-not-exist"], cwd=ROOT,
            capture_output=True, text=True, check=False,
        )
        self.assertEqual(bad.returncode, 2)
        self.assertEqual(bad.stdout, "")
        self.assertIn("unknown exercise", bad.stderr)


if __name__ == "__main__":
    unittest.main()
