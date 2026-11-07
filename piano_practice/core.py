"""Deterministic, advisory session selection; never mutates progress."""
from __future__ import annotations

from datetime import date

STATES = ("discovered", "developing", "reliable-isolation",
          "reliable-context", "maintained", "paused", "retired")
FEEDBACK = ("easy", "appropriate", "hard")
COMFORT = ("comfortable", "tension", "unknown")


def validate_catalog(catalog: dict) -> None:
    if catalog.get("schema_version") != 1:
        raise ValueError("unsupported catalog schema_version")
    exercises = catalog.get("exercises")
    if not isinstance(exercises, list) or not exercises:
        raise ValueError("catalog must have exercises")
    seen = set()
    for ex in exercises:
        if not isinstance(ex, dict) or not isinstance(ex.get("id"), str):
            raise ValueError("exercise needs an id")
        if ex["id"] in seen:
            raise ValueError("duplicate exercise id")
        seen.add(ex["id"])
        if not isinstance(ex.get("technique_id"), str) or ex.get("level") not in (0, 1):
            raise ValueError("invalid technique or level")
        if not isinstance(ex.get("notes"), list) or len(ex["notes"]) < 2 or any(
            type(n) is not int or not 0 <= n <= 127 for n in ex["notes"]
        ):
            raise ValueError("invalid note sequence")
        if type(ex.get("bpm")) is not int or not 40 <= ex["bpm"] <= 180:
            raise ValueError("invalid bpm")
        if ex.get("subdivision") not in (1, 2):
            raise ValueError("subdivision must be 1 or 2")
        if ex.get("dynamics") not in (None, "alternate"):
            raise ValueError("unsupported dynamics gate")


def validate_state(state: dict, catalog: dict) -> None:
    if state.get("schema_version") != 1 or type(state.get("revision")) is not int or state["revision"] < 0:
        raise ValueError("invalid learner state")
    sessions = state.get("sessions")
    if not isinstance(sessions, list):
        raise ValueError("sessions must be a list")
    valid_ids = {e["id"] for e in catalog["exercises"]}
    for entry in sessions:
        if entry.get("exercise_id") not in valid_ids:
            raise ValueError("unknown exercise in state")
        date.fromisoformat(entry["date"])
        if entry.get("feedback") not in FEEDBACK or entry.get("comfort") not in COMFORT:
            raise ValueError("invalid feedback or comfort")
        if entry.get("passed") is not None and type(entry["passed"]) is not bool:
            raise ValueError("passed must be boolean or null")
        if type(entry.get("approved")) is not bool:
            raise ValueError("approved must be boolean")


def propose(catalog: dict, state: dict, config: dict, on_date: str) -> dict:
    """Return a reproducible proposal from explicit inputs, without writing state.

    Selection rotates focus by least recently *approved* practice date. Level 1
    requires two approved successful level-0 sessions on distinct dates.
    Missing feedback is never treated as proficiency evidence.
    """
    validate_catalog(catalog)
    validate_state(state, catalog)
    date.fromisoformat(on_date)
    techniques = config["technique_order"]
    if len(techniques) != len(set(techniques)) or not techniques:
        raise ValueError("invalid technique order")
    allowed = {e["technique_id"] for e in catalog["exercises"]}
    if set(techniques) != allowed:
        raise ValueError("config and catalog technique IDs differ")
    active = [s for s in state["sessions"] if s["approved"] and s["date"] <= on_date]
    by_id = {e["id"]: e for e in catalog["exercises"]}
    last_by_technique = {}
    for technique in techniques:
        history = [s for s in active if by_id[s["exercise_id"]]["technique_id"] == technique]
        last_by_technique[technique] = max((s["date"] for s in history), default="")
    focus = min(techniques, key=lambda t: (last_by_technique[t], techniques.index(t)))
    choices = sorted((e for e in catalog["exercises"] if e["technique_id"] == focus),
                     key=lambda e: (e["level"], e["id"]))
    foundation = [e for e in choices if e["level"] == 0]
    advanced = [e for e in choices if e["level"] == 1]
    if len(foundation) != 1 or len(advanced) != 1:
        raise ValueError("each technique needs one exercise at each level")
    foundation = foundation[0]
    successful_dates = {
        s["date"] for s in active
        if s["exercise_id"] == foundation["id"]
        and s["passed"] is True and s["comfort"] == "comfortable"
    }
    foundation_history = sorted(
        (s for s in active if s["exercise_id"] == foundation["id"]),
        key=lambda s: s["date"],
    )
    latest_foundation = foundation_history[-1] if foundation_history else None
    regression_signal = latest_foundation is not None and (
        latest_foundation["feedback"] == "hard"
        or latest_foundation["comfort"] == "tension"
        or latest_foundation["passed"] is False
    )
    exercise = advanced[0] if len(successful_dates) >= 2 and not regression_signal else foundation
    recent = sorted(
        (s for s in active if s["exercise_id"] == exercise["id"]),
        key=lambda s: s["date"]
    )
    bpm = exercise["bpm"]
    rationale = "least recently practiced technique; no proficiency assumed"
    if recent:
        last = recent[-1]
        if last["feedback"] == "hard" or last["comfort"] == "tension" or last["passed"] is False:
            bpm = max(40, bpm - 5)
            rationale = "recent explicit difficulty: simplify tempo without advancing"
        else:
            rationale = "rotated technique using approved feedback and practice history"
    minutes = config["duration_minutes"]
    if minutes not in (15, 20, 30):
        raise ValueError("duration_minutes must be 15, 20, or 30")
    # All stage allocations remain bounded and exactly sum to duration.
    allocations = {15: (2, 2, 6, 3, 2), 20: (3, 3, 8, 4, 2), 30: (4, 4, 13, 6, 3)}
    stages = ("prepare", "baseline", "isolation", "musical-context", "verification")
    return {
        "record_type": "session-proposal",
        "contract_version": "session/v1",
        "date": on_date,
        "timezone": config["timezone"],
        "state_revision": state["revision"],
        "technique_id": focus,
        "exercise_id": exercise["id"],
        "exercise_title": exercise["title"],
        "notes_midi": exercise["notes"],
        "instructions": exercise["instructions"],
        "self_check": exercise["self_check"],
        "bpm": bpm,
        "subdivision": exercise["subdivision"],
        "minutes": minutes,
        "stages": [
            {"name": label, "minutes": amount}
            for label, amount in zip(stages, allocations[minutes])
        ],
        "fallback_minutes": 5,
        "rationale": rationale,
        "constraints": [
            "stop for pain, fatigue, or increasing tension",
            "MIDI cannot verify fingering, posture, or physical comfort",
            "proposal does not approve state transitions"
        ],
    }
