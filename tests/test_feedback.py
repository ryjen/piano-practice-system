import json
from pathlib import Path
import tempfile
import unittest

from piano_practice.feedback import apply, proposal
from piano_practice.core import MAX_SESSIONS

ROOT = Path(__file__).resolve().parents[1]


def load(path):
    return json.loads((ROOT / path).read_text(encoding="utf-8"))


class FeedbackLedgerTests(unittest.TestCase):
    def setUp(self):
        self.catalog = load("catalogs/exercises.json")
        self.state = load("examples/learner-state.json")
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.path = Path(self.temp.name) / "learner-state.json"
        self.save()

    def save(self):
        self.path.write_text(json.dumps(self.state), encoding="utf-8")

    def propose(self, state=None, **overrides):
        args = dict(event_id="take-nov-10", on_date="2026-11-10",
                    exercise_id="pulse-quarter", feedback="appropriate",
                    comfort="comfortable", passed=True, realized_bpm=60,
                    evidence_refs=["local/private-take.json"])
        args.update(overrides)
        return proposal(self.catalog, self.state if state is None else state, **args)

    def test_proposal_does_not_mutate_state(self):
        original = self.path.read_bytes()
        p = self.propose()
        self.assertEqual(original, self.path.read_bytes())
        self.assertEqual(p["state_revision"], 0)
        self.assertEqual(len(p["approval_key"]), 71)

    def test_approval_is_explicit_and_idempotent(self):
        p = self.propose()
        with self.assertRaisesRegex(ValueError, "approval key"):
            apply(self.path, self.catalog, p, "unreviewed")
        self.assertEqual(load_state(self.path)["revision"], 0)
        self.assertEqual(apply(self.path, self.catalog, p, p["approval_key"])["result"], "applied")
        written = load_state(self.path)
        self.assertEqual(written["revision"], 1)
        self.assertEqual(written["sessions"][0]["realized_bpm"], 60)
        self.assertTrue(written["sessions"][0]["approved"])
        self.assertEqual(apply(self.path, self.catalog, p, p["approval_key"])["result"],
                         "already-applied")
        self.assertEqual(load_state(self.path), written)

    def test_approval_cannot_exceed_history_bound(self):
        example = dict(date="2026-11-01", exercise_id="pulse-quarter",
                       feedback="appropriate", comfort="comfortable",
                       passed=True, approved=True)
        self.state["sessions"] = [
            {**example, "id": f"old-{i}"} for i in range(MAX_SESSIONS)
        ]
        self.save()
        p = self.propose()
        before = self.path.read_bytes()
        with self.assertRaisesRegex(ValueError, "at most"):
            apply(self.path, self.catalog, p, p["approval_key"])
        self.assertEqual(self.path.read_bytes(), before)

    def test_stale_proposal_fails_closed(self):
        p1 = self.propose()
        p2 = self.propose(event_id="take-nov-12", on_date="2026-11-12")
        apply(self.path, self.catalog, p1, p1["approval_key"])
        with self.assertRaisesRegex(ValueError, "stale state revision"):
            apply(self.path, self.catalog, p2, p2["approval_key"])
        self.assertEqual(load_state(self.path)["revision"], 1)

    def test_idempotent_retry_rejects_tampered_approved_event(self):
        p = self.propose()
        apply(self.path, self.catalog, p, p["approval_key"])
        state = load_state(self.path)
        state["sessions"][0]["passed"] = False
        self.path.write_text(json.dumps(state), encoding="utf-8")
        with self.assertRaisesRegex(ValueError, "conflicting feedback event id"):
            apply(self.path, self.catalog, p, p["approval_key"])
        self.assertEqual(load_state(self.path)["sessions"][0]["passed"], False)

    def test_idempotent_retry_rejects_tampered_event_with_extra_field(self):
        p = self.propose()
        apply(self.path, self.catalog, p, p["approval_key"])
        state = load_state(self.path)
        state["sessions"][0]["unexpected"] = True
        self.path.write_text(json.dumps(state), encoding="utf-8")
        with self.assertRaisesRegex(ValueError, "conflicting feedback event id"):
            apply(self.path, self.catalog, p, p["approval_key"])

    def test_same_id_conflicting_content_fails(self):
        p = self.propose()
        apply(self.path, self.catalog, p, p["approval_key"])
        next_state = load_state(self.path)
        other = self.propose(state=next_state, feedback="hard", passed=False)
        with self.assertRaisesRegex(ValueError, "conflicting feedback event id"):
            apply(self.path, self.catalog, other, other["approval_key"])

    def test_state_content_change_without_revision_fails_closed(self):
        p = self.propose()
        current = load_state(self.path)
        current["extra_manual_edit"] = "someone edited this without incrementing revision"
        self.path.write_text(json.dumps(current), encoding="utf-8")
        with self.assertRaisesRegex(ValueError, "state changed without revision"):
            apply(self.path, self.catalog, p, p["approval_key"])
        self.assertEqual(load_state(self.path)["revision"], 0)

    def test_catalog_change_rejected(self):
        p = self.propose()
        changed = json.loads(json.dumps(self.catalog))
        changed["exercises"][0]["title"] = "changed title"
        with self.assertRaisesRegex(ValueError, "catalog changed"):
            apply(self.path, changed, p, p["approval_key"])
        self.assertEqual(load_state(self.path)["revision"], 0)

    def test_unhashable_evidence_ref_rejected_cleanly(self):
        with self.assertRaisesRegex(ValueError, "invalid evidence reference"):
            self.propose(evidence_refs=[{"not": "a path"}])

    def test_mutated_proposal_is_rejected(self):
        p = self.propose()
        p["event"]["passed"] = False
        with self.assertRaisesRegex(ValueError, "content/key mismatch"):
            apply(self.path, self.catalog, p, p["approval_key"])

    def test_unknown_comfort_is_preserved(self):
        p = self.propose(comfort="unknown", passed=None)
        apply(self.path, self.catalog, p, p["approval_key"])
        row = load_state(self.path)["sessions"][0]
        self.assertIsNone(row["passed"])
        self.assertEqual(row["comfort"], "unknown")

    def test_evidence_path_escape_is_rejected(self):
        for path in ["../private.json", "/tmp/private.json", "https://example.com/take"]:
            with self.subTest(path=path), self.assertRaises(ValueError):
                self.propose(evidence_refs=[path])

    def test_symlink_state_rejected(self):
        fake = Path(self.temp.name) / "fake-state.json"
        fake.symlink_to(self.path)
        p = self.propose()
        with self.assertRaisesRegex(ValueError, "non-symlink"):
            apply(fake, self.catalog, p, p["approval_key"])

    def test_duplicate_event_id_does_not_change_revision(self):
        p = self.propose()
        apply(self.path, self.catalog, p, p["approval_key"])
        self.assertEqual(load_state(self.path)["revision"], 1)
        assert apply(self.path, self.catalog, p, p["approval_key"])["result"] == "already-applied"
        self.assertEqual(load_state(self.path)["revision"], 1)


def load_state(path):
    return json.loads(path.read_text(encoding="utf-8"))


if __name__ == "__main__":
    unittest.main()
