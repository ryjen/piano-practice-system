"""Repository-local reference command line interface."""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from .core import propose
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
    except (ValueError, OSError, KeyError, TypeError, RuntimeError, json.JSONDecodeError) as exc:
        print(f"pianoctl: {exc}", file=sys.stderr)
        return 2
    return 0


if __name__ == "__main__":
    sys.exit(main())
