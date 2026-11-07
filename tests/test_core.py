import copy
import json
import unittest
from pathlib import Path

from piano_practice.core import MAX_SESSIONS, propose, validate_catalog, validate_state

ROOT = Path(__file__).resolve().parents[1]


def load(p):
    return json.loads((ROOT / p).read_text(encoding="utf-8"))


class PlannerTests(unittest.TestCase):
    def setUp(self):
        self.catalog = load("catalogs/exercises.json")
        self.config = load("config/practice.json")
        # Legacy three-technique fixtures stay focused on the original slice;
        # the expanded curriculum receives independent regression coverage.
        self.catalog["exercises"] = [
            e for e in self.catalog["exercises"]
            if e["technique_id"] in ("pulse", "navigation", "dynamics")
        ]
        self.config["technique_order"] = ["pulse", "navigation", "dynamics"]
        # Legacy tests verify original least-recent behavior without weights.
        self.config.pop("goal_weights", None)
        self.config.pop("warmups", None)
        self.state = load("examples/learner-state.json")

    def add(self, date, exercise, feedback="appropriate", passed=True,
            comfort="comfortable", approved=True):
        self.state["sessions"].append(dict(
            date=date, exercise_id=exercise, feedback=feedback,
            passed=passed, comfort=comfort, approved=approved
        ))

    def test_catalog_is_valid(self):
        validate_catalog(self.catalog)

    def test_first_session_has_no_proficiency_assumption(self):
        p = propose(self.catalog, self.state, self.config, "2026-11-10")
        self.assertEqual(p["exercise_id"], "pulse-quarter")
        self.assertEqual(p["state_revision"], 0)
        self.assertEqual(sum(s["minutes"] for s in p["stages"]), 20)
        self.assertEqual(p["fallback_minutes"], 5)

    def test_rotation_prefers_unpracticed_technique(self):
        self.add("2026-11-10", "pulse-quarter")
        self.assertEqual(propose(self.catalog, self.state, self.config, "2026-11-12")["exercise_id"],
                         "navigation-steps")
        self.add("2026-11-12", "navigation-steps")
        self.assertEqual(propose(self.catalog, self.state, self.config, "2026-11-17")["exercise_id"],
                         "dynamics-contrast")

    def test_two_distinct_approved_days_are_required_to_advance(self):
        self.add("2026-11-03", "pulse-quarter")
        self.add("2026-11-03", "pulse-quarter")
        self.add("2026-11-04", "navigation-steps")
        self.add("2026-11-05", "dynamics-contrast")
        self.assertEqual(propose(self.catalog, self.state, self.config, "2026-11-10")["exercise_id"],
                         "pulse-quarter")
        self.add("2026-11-06", "pulse-quarter")
        self.add("2026-11-07", "navigation-steps")
        self.add("2026-11-08", "dynamics-contrast")
        self.assertEqual(propose(self.catalog, self.state, self.config, "2026-11-10")["exercise_id"],
                         "pulse-eighth")

    def test_hard_feedback_simplifies_not_promotes(self):
        self.add("2026-11-03", "pulse-quarter", feedback="hard", passed=False)
        self.add("2026-11-04", "navigation-steps")
        self.add("2026-11-05", "dynamics-contrast")
        proposal = propose(self.catalog, self.state, self.config, "2026-11-10")
        self.assertEqual(proposal["exercise_id"], "pulse-quarter")
        self.assertEqual(proposal["bpm"], 55)

    def test_unapproved_or_future_feedback_has_no_effect(self):
        self.add("2026-11-01", "pulse-quarter", approved=False)
        self.add("2026-11-20", "pulse-quarter")
        proposal = propose(self.catalog, self.state, self.config, "2026-11-10")
        self.assertEqual(proposal["exercise_id"], "pulse-quarter")
        self.assertEqual(proposal["bpm"], 60)

    def test_recent_failure_blocks_stage_advance(self):
        self.add("2026-11-01", "pulse-quarter")
        self.add("2026-11-02", "pulse-quarter")
        self.add("2026-11-03", "pulse-quarter", feedback="hard", passed=False)
        self.add("2026-11-04", "navigation-steps")
        self.add("2026-11-05", "dynamics-contrast")
        p = propose(self.catalog, self.state, self.config, "2026-11-10")
        self.assertEqual(p["exercise_id"], "pulse-quarter")
        self.assertEqual(p["bpm"], 55)

    def test_unknown_comfort_does_not_count_as_verified_success(self):
        for day in ("2026-11-01", "2026-11-02"):
            self.add(day, "pulse-quarter", comfort="unknown")
        self.add("2026-11-03", "navigation-steps")
        self.add("2026-11-04", "dynamics-contrast")
        self.assertEqual(propose(self.catalog, self.state, self.config, "2026-11-10")["exercise_id"],
                         "pulse-quarter")

    def test_bounded_history_and_duplicate_event_ids_fail_closed(self):
        example = dict(date="2026-11-01", exercise_id="pulse-quarter",
                       feedback="appropriate", comfort="comfortable",
                       passed=True, approved=True)
        self.state["sessions"] = [
            {**example, "id": f"session-{i}"} for i in range(MAX_SESSIONS)
        ]
        validate_state(self.state, self.catalog)
        self.state["sessions"].append({**example, "id": "session-over-limit"})
        with self.assertRaisesRegex(ValueError, "at most"):
            validate_state(self.state, self.catalog)
        self.state["sessions"].pop()
        self.state["sessions"][1]["id"] = "session-0"
        with self.assertRaisesRegex(ValueError, "duplicate"):
            validate_state(self.state, self.catalog)
        self.state["sessions"][1]["id"] = "session-1"
        self.state["sessions"][1] = None
        with self.assertRaisesRegex(ValueError, "session must be"):
            validate_state(self.state, self.catalog)

    def test_level_advance_resets_after_failure_and_requires_two_new_days(self):
        self.add("2026-11-01", "pulse-quarter")
        self.add("2026-11-02", "pulse-quarter", feedback="hard", passed=False)
        self.add("2026-11-03", "pulse-quarter")
        self.add("2026-11-04", "navigation-steps")
        self.add("2026-11-05", "dynamics-contrast")
        first = propose(self.catalog, self.state, self.config, "2026-11-10")
        self.assertEqual(first["exercise_id"], "pulse-quarter")
        self.add("2026-11-06", "pulse-quarter")
        self.add("2026-11-07", "navigation-steps")
        self.add("2026-11-08", "dynamics-contrast")
        resumed = propose(self.catalog, self.state, self.config, "2026-11-10")
        self.assertEqual(resumed["exercise_id"], "pulse-eighth")

    def test_adverse_hard_success_resets_lesson_gate(self):
        self.add("2026-11-01", "pulse-quarter")
        self.add("2026-11-02", "pulse-quarter")
        self.add("2026-11-03", "pulse-quarter",
                 feedback="hard", passed=True, comfort="comfortable")
        self.add("2026-11-04", "navigation-steps")
        self.add("2026-11-05", "dynamics-contrast")
        self.assertEqual(
            propose(self.catalog, self.state, self.config, "2026-11-10")["exercise_id"],
            "pulse-quarter"
        )
        self.add("2026-11-06", "pulse-quarter")
        self.add("2026-11-07", "navigation-steps")
        self.add("2026-11-08", "dynamics-contrast")
        self.assertEqual(
            propose(self.catalog, self.state, self.config, "2026-11-10")["exercise_id"],
            "pulse-quarter"
        )

    def test_reproducible_and_unchanged_inputs(self):
        before = copy.deepcopy(self.state)
        a = propose(self.catalog, self.state, self.config, "2026-11-10")
        b = propose(self.catalog, self.state, self.config, "2026-11-10")
        self.assertEqual(a, b)
        self.assertEqual(before, self.state)


if __name__ == "__main__":
    unittest.main()
