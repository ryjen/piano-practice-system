"""Stable 4-week simulation and explicit scheduling preference contracts."""
import copy
from collections import Counter
from datetime import date, timedelta
import json
from pathlib import Path
import subprocess
import sys
import unittest

from piano_practice.core import propose
from piano_practice.scheduling import warmups_for_prepare

ROOT = Path(__file__).resolve().parents[1]


def load(path):
    return json.loads((ROOT / path).read_text(encoding="utf-8"))


class WeightedPracticePlanTests(unittest.TestCase):
    def setUp(self):
        self.catalog = load("catalogs/exercises.json")
        self.config = load("config/practice.json")
        self.state = load("examples/learner-state.json")

    def simulate(self, config, weeks=4):
        state = copy.deepcopy(self.state)
        totals = Counter()
        sequence = []
        for i in range(weeks * 7):
            current = date(2026, 11, 10) + timedelta(days=i)
            if current.weekday() not in (1, 3):
                continue
            plan = propose(self.catalog, state, config, current.isoformat())
            self.assertEqual(sum(row["minutes"] for row in plan["stages"]),
                             config["duration_minutes"])
            totals[plan["technique_id"]] += 1
            sequence.append(plan["technique_id"])
            state["sessions"].append({
                "id": f"synthetic-{i}", "date": current.isoformat(),
                "exercise_id": plan["exercise_id"], "approved": True,
                "passed": True, "comfort": "comfortable",
                "feedback": "appropriate"
            })
        return totals, sequence

    def test_four_week_weighted_schedule_prioritizes_requested_skills(self):
        weighted, sequence = self.simulate(self.config, 4)
        self.assertEqual(sequence, [
            "reading", "coordination", "reading", "arpeggios",
            "coordination", "scale-patterns", "reading", "minor"
        ])
        self.assertEqual(weighted["reading"], 3)
        self.assertEqual(weighted["coordination"], 2)
        self.assertGreater(weighted["arpeggios"], 0)
        self.assertGreater(weighted["scale-patterns"], 0)
        legacy = copy.deepcopy(self.config)
        legacy.pop("goal_weights")
        baseline, _ = self.simulate(legacy, 4)
        self.assertGreater(weighted["reading"], baseline["reading"])
        self.assertGreater(weighted["coordination"], baseline["coordination"])

    def test_eventual_coverage_and_bounded_priorities(self):
        totals, _ = self.simulate(self.config, 36)
        self.assertEqual(set(totals), set(self.config["technique_order"]))
        self.assertGreater(totals["reading"], totals["dynamics"])
        self.assertGreater(totals["coordination"], totals["navigation"])

    def test_read_only_determinism_and_inspectable_weights(self):
        state = copy.deepcopy(self.state)
        first = propose(self.catalog, self.state, self.config, "2026-11-10")
        again = propose(self.catalog, self.state, self.config, "2026-11-10")
        self.assertEqual(first, again)
        self.assertEqual(self.state, state)
        self.assertEqual(first["selection"]["policy"], "weighted-staleness/v1")
        self.assertEqual(first["selection"]["chosen"], "reading")
        self.assertEqual(len(first["selection"]["candidate_scores"]), 11)
        self.assertEqual([s["technique_id"] for s in first["warmups_within_prepare"]],
                         ["reading", "coordination"])
        self.assertEqual(sum(s["minutes"] for s in first["warmups_within_prepare"]), 3)
        self.assertEqual(first["warmups_within_prepare"][0]["minutes"], 2)
        self.assertEqual(self.config["goal_weights"]["reading"], 5)
        self.assertGreater(self.config["goal_weights"]["reading"],
                           max(w for t, w in self.config["goal_weights"].items()
                               if t != "reading"))
        self.assertEqual(sum(s["minutes"] for s in first["stages"]), 20)

    def test_manual_focus_override_and_bad_focus_fail_closed(self):
        plan = propose(self.catalog, self.state, self.config,
                       "2026-11-10", focus_override="arpeggios")
        self.assertEqual(plan["technique_id"], "arpeggios")
        self.assertEqual(plan["selection"]["priority"], "manual-override")
        self.assertEqual(plan["exercise_id"], "arpeggio-major-one-octave")
        with self.assertRaisesRegex(ValueError, "unknown manual focus"):
            propose(self.catalog, self.state, self.config,
                    "2026-11-10", focus_override="nonexistent")
        self.assertEqual(self.state["revision"], 0)

    def test_reading_first_warmups_fit_all_supported_session_durations(self):
        expected = {15: [1, 1], 20: [2, 1], 30: [2, 1]}
        for duration, amounts in expected.items():
            with self.subTest(duration=duration):
                config = copy.deepcopy(self.config)
                config["duration_minutes"] = duration
                plan = propose(self.catalog, self.state, config, "2026-11-10")
                prepare = plan["stages"][0]["minutes"]
                rows = plan["warmups_within_prepare"]
                self.assertEqual([x["minutes"] for x in rows], amounts)
                self.assertLessEqual(sum(amounts), prepare)
                self.assertEqual(sum(x["minutes"] for x in plan["stages"]), duration)

    def test_invalid_short_session_override_fails_closed(self):
        config = copy.deepcopy(self.config)
        config["duration_minutes"] = 15
        config["warmups_by_duration"]["15"][0]["minutes"] = 2
        with self.assertRaisesRegex(ValueError, "exceed"):
            propose(self.catalog, self.state, config, "2026-11-10")

    def test_invalid_weights_and_warmups_rejected(self):
        for problem in (
            {"reading": 3},
            {**self.config["goal_weights"], "reading": True},
            {**self.config["goal_weights"], "reading": 0},
            {**self.config["goal_weights"], "reading": 6},
            {**self.config["goal_weights"], "unknown": 3},
        ):
            with self.subTest(problem=problem):
                invalid = copy.deepcopy(self.config)
                invalid["goal_weights"] = problem
                with self.assertRaises(ValueError):
                    propose(self.catalog, self.state, invalid, "2026-11-10")
        too_long = copy.deepcopy(self.config)
        too_long["warmups"][0]["minutes"] = 3
        with self.assertRaisesRegex(ValueError, "exceed"):
            propose(self.catalog, self.state, too_long, "2026-11-10")
        duplicate = copy.deepcopy(self.config)
        duplicate["warmups"][1]["technique_id"] = "reading"
        with self.assertRaisesRegex(ValueError, "invalid warmup"):
            propose(self.catalog, self.state, duplicate, "2026-11-10")

    def test_reviewed_alfred_reference_is_replayed_not_marked_complete(self):
        self.state["sessions"] = [{
            "id": "read-1", "date": "2026-11-02",
            "exercise_id": "reading-staff-steps", "approved": True,
            "passed": True, "feedback": "appropriate", "comfort": "comfortable",
            "method_book_id": "alfred-basic-adult-1",
            "method_checkpoint": "Level One section 3",
            "repertoire_id": "over-the-rainbow", "applied_revision": 1,
        }]
        plan = propose(self.catalog, self.state, self.config,
                       "2026-11-10", focus_override="reading")
        self.assertEqual(plan["previous_context_references"], [{
            "source_event_id": "read-1", "source_practice_date": "2026-11-02",
            "status": "previously-referenced; completion unknown",
            "method_book_id": "alfred-basic-adult-1",
            "method_checkpoint": "Level One section 3",
            "repertoire_id": "over-the-rainbow"
        }])
        self.assertEqual(self.state["revision"], 0)

    def test_malformed_warmup_id_and_reviewed_revision_fail_closed(self):
        bad = copy.deepcopy(self.config)
        bad["warmups"][0]["technique_id"] = {"not": "hashable"}
        with self.assertRaisesRegex(ValueError, "invalid warmup"):
            propose(self.catalog, self.state, bad, "2026-11-10")
        self.state["sessions"].append({
            "id": "reading-malformed", "date": "2026-11-01",
            "exercise_id": "reading-staff-steps", "approved": True,
            "feedback": "appropriate", "comfort": "comfortable",
            "passed": True, "method_book_id": "alfred-basic-adult-1",
            "applied_revision": "not-an-integer"
        })
        with self.assertRaisesRegex(ValueError, "invalid reviewed context"):
            propose(self.catalog, self.state, self.config, "2026-11-10",
                    focus_override="reading")

    def test_cli_focus_override_is_read_only(self):
        cmd = [sys.executable, "-m", "piano_practice.cli", "plan",
               "--date", "2026-11-10", "--focus", "scale-patterns"]
        proc = subprocess.run(cmd, cwd=ROOT, text=True, capture_output=True)
        self.assertEqual(proc.returncode, 0, proc.stderr)
        result = json.loads(proc.stdout)
        self.assertEqual(result["technique_id"], "scale-patterns")
        self.assertEqual(result["exercise_id"], "scale-crossings-two-octaves")


if __name__ == "__main__":
    unittest.main()
