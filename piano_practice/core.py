"""Deterministic, advisory session selection; never mutates progress."""
from __future__ import annotations

from datetime import date

from .timeline import onset_groups
from .scheduling import weighted_focus, warmups_for_prepare, reviewed_context

STATES = ("discovered", "developing", "reliable-isolation",
          "reliable-context", "maintained", "paused", "retired")
FEEDBACK = ("easy", "appropriate", "hard")
COMFORT = ("comfortable", "tension", "unknown")
MAX_SESSIONS = 10_000


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
        if ex.get("assessment_mode", "midi") not in ("midi", "human"):
            raise ValueError("unknown assessment mode")
        # Validate the optional explicit score/performance timeline against
        # the legacy flat MIDI pitch list at catalog admission time.
        onset_groups(ex)


def validate_state(state: dict, catalog: dict) -> None:
    if state.get("schema_version") != 1 or type(state.get("revision")) is not int or state["revision"] < 0:
        raise ValueError("invalid learner state")
    sessions = state.get("sessions")
    if not isinstance(sessions, list) or len(sessions) > MAX_SESSIONS:
        raise ValueError(f"sessions must be a list of at most {MAX_SESSIONS} records")
    valid_ids = {e["id"] for e in catalog["exercises"]}
    seen_ids = set()
    for entry in sessions:
        if not isinstance(entry, dict):
            raise ValueError("session must be an object")
        event_id = entry.get("id")
        if event_id is not None:
            if not isinstance(event_id, str) or not event_id or event_id in seen_ids:
                raise ValueError("duplicate or invalid session event id")
            seen_ids.add(event_id)
        if entry.get("exercise_id") not in valid_ids:
            raise ValueError("unknown exercise in state")
        date.fromisoformat(entry["date"])
        if entry.get("feedback") not in FEEDBACK or entry.get("comfort") not in COMFORT:
            raise ValueError("invalid feedback or comfort")
        if entry.get("passed") is not None and type(entry["passed"]) is not bool:
            raise ValueError("passed must be boolean or null")
        if type(entry.get("approved")) is not bool:
            raise ValueError("approved must be boolean")


def propose(catalog: dict, state: dict, config: dict, on_date: str,
            focus_override: str | None = None) -> dict:
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
    focus, selection = weighted_focus(
        techniques, active, by_id, on_date, config.get("goal_weights")
    )
    if focus_override is not None and focus_override not in allowed:
        raise ValueError("unknown manual focus technique")
    due = []
    if state.get("progression_events"):
        from .progression import maintenance_due
        due = maintenance_due(
            catalog, state, on_date, config.get("maintenance_interval_days", 14)
        )
    if due:
        focus = due[0]["technique_id"]
        selection["priority"] = due[0]["reason"]
    else:
        selection["priority"] = "weighted-preference" if config.get("goal_weights") else "recency"
    warnings = []
    if focus_override is not None:
        if due and focus_override != focus:
            warnings.append(
                "manual focus override defers " + due[0]["reason"] +
                " for " + due[0]["technique_id"]
            )
        focus = focus_override
        selection["priority"] = "manual-override"
    selection["chosen"] = focus
    # A manual choice can itself be in the recovery queue, even when an
    # older/high-priority obligation appears first for another technique.
    selected_due = next((item for item in due
                         if item["technique_id"] == focus), None)
    if selected_due is not None:
        selection["selected_obligation"] = dict(selected_due)
    choices = sorted((e for e in catalog["exercises"] if e["technique_id"] == focus),
                     key=lambda e: (e["level"], e["id"]))
    foundation = [e for e in choices if e["level"] == 0]
    advanced = [e for e in choices if e["level"] == 1]
    if len(foundation) != 1 or len(advanced) != 1:
        raise ValueError("each technique needs one exercise at each level")
    foundation = foundation[0]
    # Both the lesson recommendation and the formal competency gate must
    # reset after adverse evidence. Count only distinct foundation days strictly
    # after the newest adverse day for this technique. Same-day successes do not
    # demonstrate repeatability after a failure.
    technique_history = [
        s for s in active
        if by_id[s["exercise_id"]]["technique_id"] == focus
    ]
    adverse_dates = [
        s["date"] for s in technique_history
        if s["passed"] is False or s["comfort"] == "tension"
        or s["feedback"] == "hard"
    ]
    latest_adverse = max(adverse_dates, default="")
    successful_dates = {
        s["date"] for s in technique_history
        if s["exercise_id"] == foundation["id"]
        and s["passed"] is True and s["comfort"] == "comfortable"
        and s["feedback"] != "hard"
        and s["date"] > latest_adverse
    }
    regression_signal = bool(latest_adverse) and len(successful_dates) < 2
    maintenance_recovery = bool(
        selected_due and selected_due["reason"] == "adverse-feedback"
    )
    # Recovery always outranks ordinary advancement, even when historical
    # foundation successes would otherwise select the advanced exercise.
    if maintenance_recovery:
        exercise = foundation
    elif ((len(successful_dates) >= 2 and not regression_signal)
          or selected_due is not None):
        exercise = advanced[0]
    else:
        exercise = foundation
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
    if selected_due is not None:
        rationale = (
            "approved maintenance recovery required"
            if maintenance_recovery else
            "approved maintenance verification due: " + selected_due["due_date"]
        )
    elif config.get("goal_weights") is not None:
        rationale = "weighted staleness over approved practice history"
    if focus_override is not None:
        rationale = (
            rationale + "; manually selected, no proficiency claim"
            if selected_due is not None else
            "manual focus override; no proficiency claim"
        )
    minutes = config["duration_minutes"]
    if minutes not in (15, 20, 30):
        raise ValueError("duration_minutes must be 15, 20, or 30")
    # All stage allocations remain bounded and exactly sum to duration.
    allocations = {15: (2, 2, 6, 3, 2), 20: (3, 3, 8, 4, 2), 30: (4, 4, 13, 6, 3)}
    stages = ("prepare", "baseline", "isolation", "musical-context", "verification")
    warmup = warmups_for_prepare(config, allowed, allocations[minutes][0])
    context_refs = reviewed_context(active, by_id, focus)
    return {
        "record_type": "session-proposal",
        "contract_version": "session/v1",
        "date": on_date,
        "timezone": config["timezone"],
        "state_revision": state["revision"],
        "selection": selection,
        "warnings": warnings,
        "warmups_within_prepare": warmup,
        "previous_context_references": context_refs,
        "technique_id": focus,
        "exercise_id": exercise["id"],
        "exercise_title": exercise["title"],
        "notes_midi": exercise["notes"],
        "realization": {
            "contract_version": "onset-groups/v1",
            "onsets": onset_groups(exercise),
            "phases": exercise.get("realization", {}).get("phases", []),
            "finger_cues": exercise.get("realization", {}).get("finger_cues", []),
        },
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
