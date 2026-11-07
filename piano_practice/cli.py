"""Repository-local reference command line interface."""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from .core import propose
from .notation import to_musicxml
from .piango import to_piango_musicxml
from .hardware import inspect as inspect_hardware_trace
from .progression import evaluate as evaluate_progression, apply as apply_progression, maintenance_due
from .feedback import apply as apply_feedback, proposal as feedback_proposal
from .midi import assess
from .midi_io import capture, input_ports


def _load(path: str) -> dict:
    with open(path, encoding="utf-8") as stream:
        return json.load(stream)


def _print(payload) -> None:
    print(json.dumps(payload, sort_keys=True, indent=2))


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(prog="pianoctl")
    sub = parser.add_subparsers(dest="command", required=True)
    plan = sub.add_parser("plan", help="propose the next session without mutation")
    plan.add_argument("--date", required=True, help="ISO local date")
    plan.add_argument("--state", default="examples/learner-state.json")
    plan.add_argument("--catalog", default="catalogs/exercises.json")
    plan.add_argument("--config", default="config/practice.json")
    check = sub.add_parser("assess", help="evaluate a captured MIDI take")
    check.add_argument("take")
    check.add_argument("--catalog", default="catalogs/exercises.json")
    sub.add_parser("ports", help="list MIDI input ports (optional dependency)")
    record = sub.add_parser("capture", help="capture a raw MIDI take; does not assess or store it")
    record.add_argument("--port", required=True)
    record.add_argument("--exercise", required=True)
    record.add_argument("--seconds", type=float, default=20)
    record.add_argument("--bpm", type=int, help="declared practice tempo; defaults to catalog tempo when omitted")

    feedback = sub.add_parser("feedback", help="prepare or explicitly approve local session feedback")
    feedback_cmds = feedback.add_subparsers(dest="feedback_command", required=True)
    draft = feedback_cmds.add_parser("propose", help="read-only feedback proposal with approval key")
    draft.add_argument("--state", required=True, help="existing private learner state JSON")
    draft.add_argument("--catalog", default="catalogs/exercises.json")
    draft.add_argument("--id", required=True, help="unique stable feedback event id")
    draft.add_argument("--date", required=True, help="ISO local practice date")
    draft.add_argument("--exercise", required=True)
    draft.add_argument("--feedback", choices=("easy", "appropriate", "hard"), required=True)
    draft.add_argument("--comfort", choices=("comfortable", "tension", "unknown"), required=True)
    draft.add_argument("--passed", choices=("yes", "no", "unknown"), required=True)
    draft.add_argument("--bpm", required=True, type=int)
    draft.add_argument("--evidence-ref", action="append", default=[])
    draft.add_argument("--context", choices=("isolation", "musical-context"),
                       help="explicit human practice context (required for competency evidence)")
    draft.add_argument("--observation", default="", help="human-observed difficulty or correction")
    draft.add_argument("--repertoire-id", help="optional repertoire slug; metadata only")
    draft.add_argument("--timezone", default="America/Vancouver", help="IANA local practice timezone")
    draft.add_argument("--method-book-id", help="optional method-book slug")
    draft.add_argument("--method-checkpoint", help="private short page/section reference")
    approve = feedback_cmds.add_parser("apply", help="explicit, revision-safe approval of reviewed proposal")
    approve.add_argument("proposal", help="previously reviewed feedback proposal JSON")
    approve.add_argument("--state", required=True, help="existing private learner state JSON")
    approve.add_argument("--catalog", default="catalogs/exercises.json")
    approve.add_argument("--acknowledge", required=True, help="exact approval_key from reviewed proposal")

    progression = sub.add_parser("progression", help="evaluate or explicitly approve competency transitions")
    progress_cmds = progression.add_subparsers(dest="progression_command", required=True)
    evaluate = progress_cmds.add_parser("evaluate", help="read-only evidence gate evaluation")
    evaluate.add_argument("--technique", required=True)
    evaluate.add_argument("--target", required=True)
    evaluate.add_argument("--date", required=True)
    evaluate.add_argument("--state", required=True)
    evaluate.add_argument("--catalog", default="catalogs/exercises.json")
    apply_gate = progress_cmds.add_parser("apply", help="approve exact reviewed passing gate")
    apply_gate.add_argument("proposal")
    apply_gate.add_argument("--state", required=True)
    apply_gate.add_argument("--catalog", default="catalogs/exercises.json")
    apply_gate.add_argument("--acknowledge", required=True)
    due = progress_cmds.add_parser("due", help="read-only maintenance queue")
    due.add_argument("--date", required=True)
    due.add_argument("--state", required=True)
    due.add_argument("--config", default="config/practice.json")
    due.add_argument("--catalog", default="catalogs/exercises.json")

    exported = sub.add_parser("export", help="export an original practice exercise to an external score app")
    exported.add_argument("--target", required=True, choices=("piango",))
    exported.add_argument("--exercise", required=True)
    exported.add_argument("--catalog", default="catalogs/exercises.json")
    exported.add_argument("--fingering-reference", action="store_true",
                          help="include illustrative printed fingerings where the exercise defines them")

    hardware = sub.add_parser("hardware", help="inspect captured MIDI evidence without claiming physical qualification")
    hardware.add_argument("take", help="captured local midi-take/v1 JSON")
    notation = sub.add_parser("notation", help="original single-staff MusicXML exercise")
    notation.add_argument("--exercise", required=True)
    notation.add_argument("--catalog", default="catalogs/exercises.json")

    args = parser.parse_args(argv)
    try:
        if args.command == "plan":
            _print(propose(_load(args.catalog), _load(args.state), _load(args.config), args.date))
        elif args.command == "assess":
            _print(assess(_load(args.take), _load(args.catalog)))
        elif args.command == "ports":
            _print({"ports": input_ports()})
        elif args.command == "capture":
            _print(capture(args.port, args.seconds, args.exercise, args.bpm))
        elif args.command == "feedback":
            if args.feedback_command == "propose":
                passed = {"yes": True, "no": False, "unknown": None}[args.passed]
                _print(feedback_proposal(
                    _load(args.catalog), _load(args.state),
                    event_id=args.id, on_date=args.date, exercise_id=args.exercise,
                    feedback=args.feedback, comfort=args.comfort, passed=passed,
                    realized_bpm=args.bpm, evidence_refs=args.evidence_ref,
                    context=args.context, observation=args.observation,
                    repertoire_id=args.repertoire_id, timezone=args.timezone,
                    method_book_id=args.method_book_id,
                    method_checkpoint=args.method_checkpoint
                ))
            elif args.feedback_command == "apply":
                _print(apply_feedback(
                    Path(args.state), _load(args.catalog), _load(args.proposal),
                    args.acknowledge
                ))
        elif args.command == "progression":
            if args.progression_command == "evaluate":
                _print(evaluate_progression(
                    _load(args.catalog), _load(args.state), args.technique,
                    args.target, args.date
                ))
            elif args.progression_command == "apply":
                _print(apply_progression(
                    args.state, _load(args.catalog), _load(args.proposal),
                    args.acknowledge
                ))
            elif args.progression_command == "due":
                _print({"due": maintenance_due(
                    _load(args.catalog), _load(args.state), args.date,
                    _load(args.config)["maintenance_interval_days"]
                )})
        elif args.command == "export":
            sys.stdout.write(to_piango_musicxml(
                _load(args.catalog), args.exercise,
                fingering_reference=args.fingering_reference,
            ))
        elif args.command == "notation":
            sys.stdout.write(to_musicxml(_load(args.catalog), args.exercise))
        elif args.command == "hardware":
            _print(inspect_hardware_trace(_load(args.take)))
    except (ValueError, OSError, KeyError, TypeError, RuntimeError, json.JSONDecodeError) as exc:
        print(f"pianoctl: {exc}", file=sys.stderr)
        return 2
    return 0


if __name__ == "__main__":
    sys.exit(main())
