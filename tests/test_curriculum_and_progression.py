"""Regression tests for the expanded curriculum and explicit progression loop."""
import json
from pathlib import Path
import tempfile
import unittest
import xml.etree.ElementTree as ET

from piano_practice.core import propose, validate_catalog
from piano_practice.feedback import proposal as propose_feedback, apply as apply_feedback
from piano_practice.midi import assess
from piano_practice.notation import to_musicxml, spelling_to_midi
from piano_practice.progression import evaluate, apply as apply_progression, current_state, maintenance_due


ROOT = Path(__file__).resolve().parents[1]


def load(relative):
    return json.loads((ROOT / relative).read_text(encoding="utf-8"))


class CurriculumTests(unittest.TestCase):
    def setUp(self):
        self.catalog = load("catalogs/exercises.json")
        self.config = load("config/practice.json")
        self.curriculum = load("catalogs/curriculum.json")

    def test_all_user_focus_areas_have_two_levels_and_unique_ids(self):
        validate_catalog(self.catalog)
        techniques = set(self.config["technique_order"])
        self.assertEqual(len(techniques), 9)
        self.assertEqual(techniques, {x["technique_id"] for x in self.catalog["exercises"]})
        for technique in techniques:
            self.assertEqual(
                sorted(x["level"] for x in self.catalog["exercises"] if x["technique_id"] == technique),
                [0, 1],
            )
        self.assertEqual(len(self.catalog["exercises"]), 18)

    def test_method_books_and_recital_examples_reference_known_techniques(self):
        ids = [x["id"] for x in self.curriculum["repertoire"]]
        self.assertEqual(ids, ["fur-elise", "over-the-rainbow", "jacobs-ladder"])
        self.assertEqual(
            {x["id"] for x in self.curriculum["method_books"]},
            {"alfred-basic-adult-1", "alfred-basic-adult-2"}
        )
        for item in self.curriculum["repertoire"]:
            self.assertTrue(set(item["focus_techniques"]) <= set(self.config["technique_order"]))
        self.assertEqual(self.curriculum["schema_version"], 1)

    def test_reading_score_musicxml_is_original_and_pitches_match(self):
        xml = to_musicxml(self.catalog, "reading-accidentals")
        root = ET.fromstring(xml)
        notes = root.findall(".//part/measure/note")
        pitches = []
        for n in notes:
            pitch = n.find("pitch")
            if pitch is None:
                continue
            step = pitch.findtext("step")
            alter = int(pitch.findtext("alter", "0"))
            octave = pitch.findtext("octave")
            mark = "#" if alter == 1 else "b" if alter == -1 else ""
            pitches.append(spelling_to_midi(step + mark + octave))
        expected = next(e for e in self.catalog["exercises"]
                        if e["id"] == "reading-accidentals")["notes"]
        self.assertEqual(pitches, expected)
        self.assertIn("<accidental>flat</accidental>", xml)
        self.assertIn("<accidental>sharp</accidental>", xml)

    def test_manual_reading_and_two_hands_can_never_pass_on_midi_alone(self):
        take = load("examples/midi-takes/pulse-quarter-pass.json")
        for ex_id in ("reading-staff-steps", "coordination-alternating",
                      "circle-fourths", "triads-root"):
            with self.subTest(exercise=ex_id):
                take["exercise_id"] = ex_id
                result = assess(take, self.catalog)
                self.assertEqual(result["checks"]["required_human_observation"], "unknown")
                self.assertFalse(result["pass"])

    def test_planner_rotates_into_user_focus_areas(self):
        state = load("examples/learner-state.json")
        for i, (technique, exercise) in enumerate((
            ("pulse", "pulse-quarter"),
            ("navigation", "navigation-steps"),
            ("dynamics", "dynamics-contrast"),
        )):
            state["sessions"].append({
                "id": f"old-{i}", "date": f"2026-11-0{i+1}",
                "exercise_id": exercise, "approved": True,
                "feedback": "appropriate", "comfort": "comfortable", "passed": True
            })
        plan = propose(self.catalog, state, self.config, "2026-11-10")
        self.assertEqual(plan["technique_id"], "reading")
        self.assertEqual(plan["exercise_id"], "reading-staff-steps")


class ProgressionTests(unittest.TestCase):
    def setUp(self):
        self.catalog = load("catalogs/exercises.json")
        self.config = load("config/practice.json")
        self.root = tempfile.TemporaryDirectory()
        self.addCleanup(self.root.cleanup)
        self.state_path = Path(self.root.name) / "learner-state.json"
        self.state_path.write_text(json.dumps(load("examples/learner-state.json")), encoding="utf-8")

    def state(self):
        return json.loads(self.state_path.read_text(encoding="utf-8"))

    def session(self, n, date, *, context="isolation", comfort="comfortable",
                passed=True, feedback="appropriate", repertoire_id=None,
                exercise_id="reading-staff-steps", method_book_id=None,
                method_checkpoint=None):
        state = self.state()
        p = propose_feedback(
            self.catalog, state,
            event_id=f"session-{n}", on_date=date, exercise_id=exercise_id,
            feedback=feedback, comfort=comfort, passed=passed, realized_bpm=60,
            evidence_refs=[], context=context, observation="My own reading check",
            repertoire_id=repertoire_id,
            method_book_id=method_book_id, method_checkpoint=method_checkpoint
        )
        outcome = apply_feedback(self.state_path, self.catalog, p, p["approval_key"])
        self.assertEqual(outcome["result"], "applied")
        return p

    def transition(self, target, date, *, apply=True):
        p = evaluate(self.catalog, self.state(), "reading", target, date)
        if apply:
            self.assertEqual(p["gate"], "pass", p)
            result = apply_progression(str(self.state_path), self.catalog, p, p["approval_key"])
            self.assertEqual(result["result"], "applied")
        return p

    def test_full_successive_progression_and_maintenance_due(self):
        self.session(1, "2026-11-01")
        self.transition("developing", "2026-11-02")
        self.session(2, "2026-11-03")
        blocked = self.transition("reliable-isolation", "2026-11-03", apply=False)
        self.assertEqual(blocked["gate"], "blocked")
        self.session(3, "2026-11-04")
        self.transition("reliable-isolation", "2026-11-05")
        self.session(4, "2026-11-06", context="musical-context", repertoire_id="fur-elise")
        self.session(5, "2026-11-07", context="musical-context", repertoire_id="fur-elise")
        self.transition("reliable-context", "2026-11-08")
        self.session(6, "2026-11-09", context="musical-context")
        self.session(7, "2026-11-10", context="musical-context")
        self.transition("maintained", "2026-11-11")
        self.assertEqual(current_state(self.state(), "reading")[0], "maintained")
        self.assertEqual(maintenance_due(self.catalog, self.state(), "2026-11-24", 14), [])
        due = maintenance_due(self.catalog, self.state(), "2026-11-25", 14)
        self.assertEqual(len(due), 1)
        self.assertEqual(due[0]["technique_id"], "reading")
        plan = propose(self.catalog, self.state(), self.config, "2026-11-25")
        self.assertEqual(plan["technique_id"], "reading")
        self.assertIn("maintenance", plan["rationale"])
        self.session(8, "2026-11-25", context="musical-context")
        self.assertEqual(maintenance_due(self.catalog, self.state(), "2026-11-25", 14), [])
        self.assertEqual(plan["technique_id"], "reading")
        self.session(9, "2026-11-26", context="musical-context", passed=False, feedback="hard")
        recovery = maintenance_due(self.catalog, self.state(), "2026-11-26", 14)
        self.assertEqual(recovery[0]["reason"], "adverse-feedback")
        next_plan = propose(self.catalog, self.state(), self.config, "2026-11-26")
        self.assertEqual(next_plan["exercise_id"], "reading-staff-steps")
        self.assertIn("recovery", next_plan["rationale"])
        decline = self.transition("reliable-context", "2026-11-27", apply=False)
        self.assertEqual(decline["gate"], "pass")
        self.transition("reliable-context", "2026-11-27")
        self.assertEqual(current_state(self.state(), "reading")[0], "reliable-context")
        self.assertEqual(maintenance_due(self.catalog, self.state(), "2026-11-27", 14), [])

    def test_unknown_and_v1_observations_do_not_pass_competency_gate(self):
        legacy = propose_feedback(self.catalog, self.state(), event_id="legacy", on_date="2026-11-01",
                                  exercise_id="reading-staff-steps", feedback="appropriate",
                                  comfort="comfortable", passed=True, realized_bpm=60)
        apply_feedback(self.state_path, self.catalog, legacy, legacy["approval_key"])
        self.assertEqual(self.transition("developing", "2026-11-02", apply=False)["gate"], "blocked")
        self.session(1, "2026-11-03", comfort="unknown", passed=None)
        self.assertEqual(self.transition("developing", "2026-11-04", apply=False)["gate"], "blocked")

    def test_tampering_with_supporting_feedback_invalidates_approved_history(self):
        self.session(1, "2026-11-01")
        self.transition("developing", "2026-11-02")
        state = self.state()
        state["sessions"][0]["passed"] = False
        self.state_path.write_text(json.dumps(state), encoding="utf-8")
        with self.assertRaisesRegex(ValueError, "unsupported positive progression evidence"):
            evaluate(self.catalog, self.state(), "reading", "reliable-isolation",
                     "2026-11-06")

    def test_unscoped_observation_requires_v2_context(self):
        with self.assertRaisesRegex(ValueError, "context is required"):
            propose_feedback(self.catalog, self.state(), event_id="unscoped",
                             on_date="2026-11-01", exercise_id="reading-staff-steps",
                             feedback="appropriate", comfort="unknown", passed=None,
                             realized_bpm=60, observation="I read the sheet")

    def test_same_day_duplicate_does_not_prove_repeatability(self):
        self.session(1, "2026-11-01")
        self.transition("developing", "2026-11-02")
        self.session(2, "2026-11-03")
        self.session(3, "2026-11-03")
        self.assertEqual(
            self.transition("reliable-isolation", "2026-11-04", apply=False)["gate"],
            "blocked"
        )

    def test_progression_gate_requires_explicit_review_and_is_idempotent(self):
        self.session(1, "2026-11-01")
        p = self.transition("developing", "2026-11-02", apply=False)
        with self.assertRaises(ValueError):
            apply_progression(str(self.state_path), self.catalog, p, "wrong-key")
        self.assertEqual(apply_progression(str(self.state_path), self.catalog, p, p["approval_key"])["result"],
                         "applied")
        self.assertEqual(apply_progression(str(self.state_path), self.catalog, p, p["approval_key"])["result"],
                         "already-applied")

    def test_stale_and_conflicting_revision_fail_closed(self):
        self.session(1, "2026-11-01")
        p = self.transition("developing", "2026-11-02", apply=False)
        self.session(2, "2026-11-02")
        with self.assertRaisesRegex(ValueError, "stale"):
            apply_progression(str(self.state_path), self.catalog, p, p["approval_key"])

    def test_explicit_adverse_report_requires_recovery_before_promotion(self):
        self.session(1, "2026-11-01")
        self.transition("developing", "2026-11-02")
        self.session(2, "2026-11-03")
        self.session(3, "2026-11-04", passed=False, feedback="hard")
        self.assertEqual(self.transition("reliable-isolation", "2026-11-05", apply=False)["gate"], "blocked")
        self.session(4, "2026-11-06")
        self.assertEqual(self.transition("reliable-isolation", "2026-11-07", apply=False)["gate"], "blocked")
        self.session(5, "2026-11-08")
        self.assertEqual(self.transition("reliable-isolation", "2026-11-09", apply=False)["gate"], "pass")

    def test_same_day_post_approval_adverse_requires_recovery(self):
        # All musical practice dates and transition approvals are explicit.
        self.session(1, "2026-11-01")
        self.transition("developing", "2026-11-02")
        self.session(2, "2026-11-03")
        self.session(3, "2026-11-04")
        self.transition("reliable-isolation", "2026-11-05")
        self.session(4, "2026-11-06", context="musical-context")
        self.session(5, "2026-11-07", context="musical-context")
        self.transition("reliable-context", "2026-11-08")
        self.session(6, "2026-11-09", context="musical-context")
        self.session(7, "2026-11-10", context="musical-context")
        self.transition("maintained", "2026-11-11")
        before = self.state()
        approval_revision = before["progression_events"][-1]["applied_revision"]

        # An advanced-exercise failure is approved later on the SAME date.
        self.session(8, "2026-11-11", exercise_id="reading-accidentals",
                     context="musical-context", passed=False, feedback="hard",
                     comfort="tension")
        after = self.state()
        self.assertGreater(after["sessions"][-1]["applied_revision"], approval_revision)
        due = maintenance_due(self.catalog, after, "2026-11-13", 14)
        self.assertEqual(due[0]["reason"], "adverse-feedback")
        plan = propose(self.catalog, after, self.config, "2026-11-13")
        self.assertEqual(plan["exercise_id"], "reading-staff-steps")
        self.assertIn("recovery", plan["rationale"])
        self.assertEqual(
            self.transition("reliable-context", "2026-11-13", apply=False)["gate"],
            "pass"
        )
        self.transition("reliable-context", "2026-11-13")
        self.assertEqual(current_state(self.state(), "reading")[0], "reliable-context")

    def test_method_checkpoint_timezone_and_event_revision(self):
        p = self.session(1, "2026-11-01", method_book_id="alfred-basic-adult-1",
                         method_checkpoint="Level One section 3 (private reference)")
        row = self.state()["sessions"][0]
        self.assertEqual(p["contract_version"], "feedback/v2")
        self.assertEqual(row["timezone"], "America/Vancouver")
        self.assertEqual(row["method_book_id"], "alfred-basic-adult-1")
        self.assertEqual(row["method_checkpoint"],
                         "Level One section 3 (private reference)")
        self.assertEqual(row["applied_revision"], 1)
        self.assertEqual(apply_feedback(self.state_path, self.catalog,
                                        p, p["approval_key"])["result"], "already-applied")
        changed = self.state()
        changed["sessions"][0]["applied_revision"] = 2
        self.state_path.write_text(json.dumps(changed), encoding="utf-8")
        with self.assertRaisesRegex(ValueError, "conflicting feedback"):
            apply_feedback(self.state_path, self.catalog, p, p["approval_key"])

    def test_bad_timezone_or_checkpoint_without_book_rejected(self):
        state = self.state()
        common = dict(event_id="invalid", on_date="2026-11-01",
                      exercise_id="reading-staff-steps", feedback="appropriate",
                      comfort="comfortable", passed=True, realized_bpm=60,
                      context="isolation")
        with self.assertRaisesRegex(ValueError, "invalid IANA timezone"):
            propose_feedback(self.catalog, state, timezone="Nowhere/NoZone", **common)
        with self.assertRaisesRegex(ValueError, "checkpoint requires a method book"):
            propose_feedback(self.catalog, state, method_checkpoint="p.1", **common)

    def test_hard_feedback_cannot_support_historical_positive_gate(self):
        self.session(1, "2026-11-01")
        completed = self.transition("developing", "2026-11-02")
        state = self.state()
        state["sessions"][0]["feedback"] = "hard"
        self.state_path.write_text(json.dumps(state), encoding="utf-8")
        with self.assertRaisesRegex(ValueError, "unsupported positive progression evidence"):
            evaluate(self.catalog, self.state(), "reading", "reliable-isolation",
                     "2026-11-06")
        with self.assertRaisesRegex(ValueError, "unsupported positive progression evidence"):
            apply_progression(str(self.state_path), self.catalog, completed,
                              completed["approval_key"])

    def test_backdated_promotion_cannot_ignore_later_approved_failure(self):
        self.session(1, "2026-11-01")
        self.transition("developing", "2026-11-02")
        self.session(2, "2026-11-03")
        self.session(3, "2026-11-04")
        self.session(4, "2026-11-05", passed=False, feedback="hard")
        historical = self.transition("reliable-isolation", "2026-11-04", apply=False)
        self.assertEqual(historical["gate"], "pass")  # Historical query is allowed.
        with self.assertRaisesRegex(ValueError, "backdated transition"):
            apply_progression(str(self.state_path), self.catalog, historical,
                              historical["approval_key"])
        self.assertEqual(current_state(self.state(), "reading")[0], "developing")
        self.assertEqual(
            self.transition("reliable-isolation", "2026-11-06", apply=False)["gate"],
            "blocked"
        )

    def test_later_other_technique_feedback_does_not_block_transition(self):
        self.session(1, "2026-11-01")
        state = self.state()
        extra = propose_feedback(
            self.catalog, state, event_id="pulse-unrelated", on_date="2026-11-05",
            exercise_id="pulse-quarter", feedback="appropriate",
            comfort="comfortable", passed=True, realized_bpm=60,
            context="isolation"
        )
        apply_feedback(self.state_path, self.catalog, extra, extra["approval_key"])
        approved = self.transition("developing", "2026-11-02")
        self.assertEqual(approved["gate"], "pass")

    def test_negative_gate_cannot_be_applied(self):
        p = self.transition("developing", "2026-11-02", apply=False)
        self.assertEqual(p["gate"], "blocked")
        with self.assertRaisesRegex(ValueError, "gate not passed"):
            apply_progression(str(self.state_path), self.catalog, p, p["approval_key"])


if __name__ == "__main__":
    unittest.main()
