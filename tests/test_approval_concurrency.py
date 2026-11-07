"""Cross-process contention test for single-user POSIX approval writers."""
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

from piano_practice.feedback import apply as apply_feedback, proposal as propose_feedback
from piano_practice.progression import evaluate as evaluate_progression

ROOT = Path(__file__).resolve().parents[1]


@unittest.skipUnless(os.name == "posix", "requires POSIX fcntl file locking")
class ContentionTests(unittest.TestCase):
    def test_feedback_and_progression_approval_share_a_revision_lock(self):
        catalog = json.loads((ROOT / "catalogs/exercises.json").read_text(encoding="utf-8"))
        initial = json.loads((ROOT / "examples/learner-state.json").read_text(encoding="utf-8"))
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "learner-state.json"
            path.write_text(json.dumps(initial), encoding="utf-8")
            p0 = propose_feedback(
                catalog, initial, event_id="practice-first", on_date="2026-11-01",
                exercise_id="reading-staff-steps", feedback="appropriate",
                comfort="comfortable", passed=True, realized_bpm=60,
                context="isolation", observation="identified each printed note"
            )
            apply_feedback(path, catalog, p0, p0["approval_key"])
            state = json.loads(path.read_text(encoding="utf-8"))
            self.assertEqual(state["revision"], 1)
            progression = evaluate_progression(catalog, state, "reading", "developing", "2026-11-02")
            next_feedback = propose_feedback(
                catalog, state, event_id="practice-second", on_date="2026-11-03",
                exercise_id="reading-staff-steps", feedback="appropriate",
                comfort="comfortable", passed=True, realized_bpm=60,
                context="isolation", observation="verified another pass"
            )
            progression_path = Path(tmp) / "progression.json"
            feedback_path = Path(tmp) / "feedback.json"
            progression_path.write_text(json.dumps(progression), encoding="utf-8")
            feedback_path.write_text(json.dumps(next_feedback), encoding="utf-8")
            base = [sys.executable, "-m", "piano_practice.cli"]
            cmds = [
                base + ["progression", "apply", str(progression_path),
                        "--state", str(path), "--acknowledge", progression["approval_key"]],
                base + ["feedback", "apply", str(feedback_path),
                        "--state", str(path), "--acknowledge", next_feedback["approval_key"]],
            ]
            procs = [subprocess.Popen(command, cwd=ROOT, stdout=subprocess.PIPE,
                                     stderr=subprocess.PIPE, text=True)
                     for command in cmds]
            results = [(p.returncode, out, err) for p in procs
                       for out, err in [p.communicate(timeout=10)]]
            self.assertEqual(sum(code == 0 for code, _, _ in results), 1, results)
            self.assertEqual(sum(code == 2 for code, _, _ in results), 1, results)
            self.assertTrue(any("stale" in err for code, _, err in results if code == 2), results)
            final = json.loads(path.read_text(encoding="utf-8"))
            self.assertEqual(final["revision"], 2)
            self.assertEqual(len(final["sessions"]) +
                             len(final.get("progression_events", [])), 2)


if __name__ == "__main__":
    unittest.main()
