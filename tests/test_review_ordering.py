"""Cross-technique maintenance priority regression."""
import json
from pathlib import Path
import tempfile
import unittest

from piano_practice.core import propose
from piano_practice.feedback import proposal as feedback_proposal, apply as apply_feedback
from piano_practice.progression import evaluate, apply as apply_transition, maintenance_due

ROOT = Path(__file__).resolve().parents[1]


class MaintenancePriorityTests(unittest.TestCase):
    def setUp(self):
        self.catalog = json.loads((ROOT / "catalogs/exercises.json").read_text())
        self.config = json.loads((ROOT / "config/practice.json").read_text())
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.path = Path(self.temp.name) / "learner-state.json"
        self.path.write_text(json.dumps({"schema_version": 1, "revision": 0, "sessions": []}))
        self.sequence = 0

    def state(self):
        return json.loads(self.path.read_text())

    def record(self, technique, day, *, context="isolation", passed=True):
        self.sequence += 1
        exercise = next(e for e in self.catalog["exercises"]
                        if e["technique_id"] == technique and e["level"] == 0)
        candidate = feedback_proposal(
            self.catalog, self.state(), event_id=f"practice-{self.sequence}",
            on_date=day, exercise_id=exercise["id"], realized_bpm=exercise["bpm"],
            feedback="appropriate" if passed else "hard",
            comfort="comfortable" if passed else "tension",
            passed=passed, context=context, observation="human self-check"
        )
        apply_feedback(self.path, self.catalog, candidate, candidate["approval_key"])

    def promote(self, technique, target, day):
        candidate = evaluate(self.catalog, self.state(), technique, target, day)
        self.assertEqual(candidate["gate"], "pass", candidate)
        apply_transition(str(self.path), self.catalog, candidate, candidate["approval_key"])

    def establish_maintained(self, technique, month):
        def date(n): return f"2026-{month:02d}-{n:02d}"
        self.record(technique, date(1))
        self.promote(technique, "developing", date(2))
        self.record(technique, date(3))
        self.record(technique, date(4))
        self.promote(technique, "reliable-isolation", date(5))
        self.record(technique, date(6), context="musical-context")
        self.record(technique, date(7), context="musical-context")
        self.promote(technique, "reliable-context", date(8))
        self.record(technique, date(9), context="musical-context")
        self.record(technique, date(10), context="musical-context")
        self.promote(technique, "maintained", date(11))

    def test_recovery_precedes_older_routine_due_date(self):
        self.establish_maintained("reading", 10)
        self.establish_maintained("pulse", 11)
        self.record("pulse", "2026-11-12", context="musical-context", passed=False)
        due = maintenance_due(self.catalog, self.state(), "2026-11-12", 14)
        self.assertEqual(
            [(x["technique_id"], x["reason"]) for x in due],
            [("pulse", "adverse-feedback"), ("reading", "maintenance-due")]
        )
        next_session = propose(self.catalog, self.state(), self.config, "2026-11-12")
        self.assertEqual(next_session["technique_id"], "pulse")
        self.assertEqual(next_session["exercise_id"], "pulse-quarter")
        self.assertIn("recovery", next_session["rationale"])
        override = propose(
            self.catalog, self.state(), self.config,
            "2026-11-12", focus_override="arpeggios"
        )
        self.assertEqual(override["technique_id"], "arpeggios")
        self.assertEqual(override["selection"]["priority"], "manual-override")
        self.assertIn("defers adverse-feedback for pulse", override["warnings"][0])
        self.assertEqual(override["exercise_id"], "arpeggio-major-one-octave")


if __name__ == "__main__":
    unittest.main()
