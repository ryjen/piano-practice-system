"""Deterministic, evidence-bound competency proposals and review-only transitions.

Feedback/v2 states the musical context explicitly. A difficulty level does
not prove contextual competence; MIDI is never physical technique evidence.
"""
from __future__ import annotations

from datetime import date, timedelta
import hashlib

from .core import STATES, validate_catalog, validate_state
from .feedback import canonical
from .state_store import transact

ORDER = ("discovered", "developing", "reliable-isolation",
         "reliable-context", "maintained")
RULESET = "progression/v1"
REQUIRED = {
    "developing": ("any", 1),
    "reliable-isolation": ("isolation", 2),
    "reliable-context": ("musical-context", 2),
    "maintained": ("musical-context", 2),
}
_EVENT_KEYS = {"id", "technique_id", "from_state", "to_state",
               "effective_date", "evidence_ids", "ruleset_version",
               "approval_key", "approved", "applied_revision"}


def _iso(raw: str) -> date:
    if not isinstance(raw, str):
        raise ValueError("expected ISO date")
    d = date.fromisoformat(raw)
    if d.isoformat() != raw:
        raise ValueError("noncanonical ISO date")
    return d


def _technique_ids(catalog: dict) -> set[str]:
    return {e["technique_id"] for e in catalog["exercises"]}


def validate_events(state: dict, catalog: dict) -> None:
    events = state.get("progression_events", [])
    if not isinstance(events, list) or len(events) > 10000:
        raise ValueError("invalid progression history")
    ids = set()
    by_technique = {}
    latest_event_date = {}
    latest_event_revision = {}
    approved_feedback = {}
    for session in state["sessions"]:
        if not session.get("approved") or not isinstance(session.get("id"), str):
            continue
        if session["id"] in approved_feedback:
            raise ValueError("duplicate approved feedback ID")
        approved_feedback[session["id"]] = session
    exercise_owner = {e["id"]: e["technique_id"] for e in catalog["exercises"]}
    for event in events:
        if not isinstance(event, dict) or set(event) != _EVENT_KEYS:
            raise ValueError("invalid progression event")
        if (not isinstance(event["id"], str) or not event["id"].startswith("progression-")
                or event["id"] in ids):
            raise ValueError("duplicate or invalid progression event id")
        ids.add(event["id"])
        technique = event["technique_id"]
        if technique not in _technique_ids(catalog):
            raise ValueError("unknown progression technique")
        if event["ruleset_version"] != RULESET or event["approved"] is not True:
            raise ValueError("invalid ruleset or unapproved progression event")
        if event["from_state"] not in ORDER or event["to_state"] not in ORDER:
            raise ValueError("unsupported progression state")
        prev = by_technique.get(technique, "discovered")
        if event["from_state"] != prev:
            raise ValueError("progression history is not contiguous")
        nxt = event["to_state"]
        forward = ORDER.index(nxt) == ORDER.index(prev) + 1
        regression = ORDER.index(prev) > 1 and ORDER.index(nxt) == ORDER.index(prev) - 1
        if not (forward or regression):
            raise ValueError("illegal progression transition")
        current_date = _iso(event["effective_date"])
        previous_date = latest_event_date.get(technique)
        previous_revision = latest_event_revision.get(technique)
        if previous_date is not None and current_date < previous_date:
            raise ValueError("non-monotonic progression dates")
        revision = event["applied_revision"]
        if (type(revision) is not int or revision <= 0 or revision > state["revision"]
                or (previous_revision is not None and revision <= previous_revision)):
            raise ValueError("invalid progression approval order")
        refs = event["evidence_ids"]
        if not isinstance(refs, list) or not refs or len(refs) != len(set(refs)):
            raise ValueError("invalid supporting evidence IDs")
        if any(not isinstance(ref, str) or not ref for ref in refs):
            raise ValueError("invalid evidence reference")
        if not isinstance(event["approval_key"], str) or not event["approval_key"].startswith("sha256:"):
            raise ValueError("invalid approval reference")
        referenced = []
        for ref in refs:
            session = approved_feedback.get(ref)
            if session is None or exercise_owner.get(session["exercise_id"]) != technique:
                raise ValueError("progression evidence absent or belongs to different technique")
            if session.get("context") not in ("isolation", "musical-context"):
                raise ValueError("legacy/unscoped feedback cannot prove competency")
            observed_on = _iso(session["date"])
            session_revision = session.get("applied_revision")
            if (type(session_revision) is not int or not 0 < session_revision < revision
                    or observed_on > current_date):
                raise ValueError("progression evidence outside the approved transition window")
            if previous_date is not None:
                if observed_on < previous_date:
                    raise ValueError("progression evidence precedes previous transition")
                if observed_on == previous_date and (
                    forward or previous_revision is None or session_revision <= previous_revision
                ):
                    raise ValueError("same-day evidence must be adverse and approved after prior transition")
            referenced.append(session)
        if forward:
            scope, needed = REQUIRED[nxt]
            if len({s["date"] for s in referenced}) < needed:
                raise ValueError("progression requires distinct evidence dates")
            if any(s["passed"] is not True or s["comfort"] != "comfortable"
                   or s["feedback"] == "hard"
                   or (scope != "any" and s["context"] != scope) for s in referenced):
                raise ValueError("unsupported positive progression evidence")
        elif not any(s["passed"] is False or s["comfort"] == "tension"
                     or s["feedback"] == "hard" for s in referenced):
            raise ValueError("regression requires explicit adverse evidence")
        by_technique[technique] = nxt
        latest_event_date[technique] = current_date
        latest_event_revision[technique] = revision


def current_state(state: dict, technique_id: str) -> tuple[str, str | None]:
    matched = [e for e in state.get("progression_events", [])
               if e["technique_id"] == technique_id]
    if not matched:
        return "discovered", None
    return matched[-1]["to_state"], matched[-1]["effective_date"]


def _eligible_feedback(state: dict, catalog: dict, technique_id: str,
                       as_of: date, after: date | None,
                       after_revision: int | None = None) -> list[dict]:
    by_id = {ex["id"]: ex["technique_id"] for ex in catalog["exercises"]}
    # Only feedback/v2 entries with explicit context and unique stable IDs
    # can establish a competency gate. Legacy feedback/v1 stays unknown.
    eligible = []
    seen = set()
    for entry in state["sessions"]:
        if not entry["approved"] or by_id[entry["exercise_id"]] != technique_id:
            continue
        d = _iso(entry["date"])
        if d > as_of:
            continue
        if after is not None:
            if d < after:
                continue
            if d == after:
                # Without times of day, only explicitly adverse feedback
                # approved AFTER the transition can trigger same-day recovery.
                is_adverse = (entry["passed"] is False or
                              entry["comfort"] == "tension" or
                              entry["feedback"] == "hard")
                revision = entry.get("applied_revision")
                if (not is_adverse or after_revision is None or
                        type(revision) is not int or revision <= after_revision):
                    continue
        entry_id = entry.get("id")
        if not isinstance(entry_id, str) or not entry_id or entry_id in seen:
            continue
        seen.add(entry_id)
        if entry.get("context") not in ("isolation", "musical-context"):
            continue
        eligible.append(entry)
    return sorted(eligible, key=lambda e: (e["date"], e["id"]))


def evaluate(catalog: dict, state: dict, technique_id: str, target_state: str,
             as_of: str) -> dict:
    validate_catalog(catalog)
    validate_state(state, catalog)
    validate_events(state, catalog)
    if technique_id not in _technique_ids(catalog):
        raise ValueError("unknown technique")
    day = _iso(as_of)
    previous, last_transition = current_state(state, technique_id)
    if target_state not in ORDER or previous == target_state:
        raise ValueError("unsupported or unchanged target")
    forward = ORDER.index(target_state) == ORDER.index(previous) + 1
    regression = ORDER.index(previous) > 1 and ORDER.index(target_state) == ORDER.index(previous) - 1
    if not (forward or regression):
        raise ValueError("unsupported progression edge")
    after = _iso(last_transition) if last_transition else None
    if after is not None and day < after:
        raise ValueError("assessment date precedes approved progression state")
    previous_event = next(
        (e for e in reversed(state.get("progression_events", []))
         if e["technique_id"] == technique_id), None
    )
    records = _eligible_feedback(
        state, catalog, technique_id, day, after,
        previous_event["applied_revision"] if previous_event else None
    )
    positive = [e for e in records if
                e["passed"] is True and e["comfort"] == "comfortable"]
    adverse = [e for e in records if
               e["passed"] is False or e["comfort"] == "tension"
               or e["feedback"] == "hard"]
    if regression:
        chosen = adverse[-1:]  # A regression is never automatic.
        result = "pass" if chosen else "blocked"
        reason = "explicit adverse feedback since approved transition" if chosen else "no adverse evidence"
    else:
        scope, needed = REQUIRED[target_state]
        # A failure resets the required streak; old good dates cannot
        # combine with a single post-failure success to promote a technique.
        most_recent_adverse = max((e["date"] for e in adverse), default="")
        selected = [e for e in positive if
                    (scope == "any" or e["context"] == scope)
                    and e["date"] > most_recent_adverse]
        unique_dates = []
        chosen = []
        for entry in selected:
            if entry["date"] not in unique_dates:
                unique_dates.append(entry["date"])
                chosen.append(entry)
        chosen = chosen[:needed]
        enough = len(chosen) == needed
        result = "pass" if enough else "blocked"
        reason = "distinct approved days and explicit context" if result == "pass" else (
            f"need {needed} distinct approved comfortable pass dates after latest adverse"
            f" feedback in {scope} context"
        )
    bare = {
        "record_type": "progression-proposal",
        "contract_version": RULESET,
        "technique_id": technique_id,
        "from_state": previous,
        "to_state": target_state,
        "effective_date": as_of,
        "gate": result,
        "gate_reason": reason,
        "evidence_ids": [e["id"] for e in chosen],
        "state_revision": state["revision"],
        "state_digest": "sha256:" + hashlib.sha256(canonical(state)).hexdigest(),
        "catalog_digest": "sha256:" + hashlib.sha256(canonical(catalog)).hexdigest(),
    }
    return {**bare, "approval_key": "sha256:" + hashlib.sha256(canonical(bare)).hexdigest()}


def apply(path: str, catalog: dict, proposal: dict, acknowledgement: str) -> dict:
    validate_catalog(catalog)
    if not isinstance(proposal, dict) or set(proposal) != {
        "record_type", "contract_version", "technique_id", "from_state", "to_state",
        "effective_date", "gate", "gate_reason", "evidence_ids", "state_revision",
        "state_digest", "catalog_digest", "approval_key"
    }:
        raise ValueError("invalid progression proposal")
    if proposal["record_type"] != "progression-proposal" or proposal["contract_version"] != RULESET:
        raise ValueError("wrong progression contract")
    bare = {k: v for k, v in proposal.items() if k != "approval_key"}
    key = "sha256:" + hashlib.sha256(canonical(bare)).hexdigest()
    if acknowledgement != key or proposal["approval_key"] != key:
        raise ValueError("unreviewed progression proposal")
    if proposal["gate"] != "pass":
        raise ValueError("progression gate not passed")
    if proposal["catalog_digest"] != "sha256:" + hashlib.sha256(canonical(catalog)).hexdigest():
        raise ValueError("catalog changed since assessment")
    event_id = "progression-" + key[7:31]

    def update(state: dict) -> tuple[dict | None, dict]:
        validate_state(state, catalog)
        validate_events(state, catalog)
        matches = [e for e in state.get("progression_events", []) if e["id"] == event_id]
        if matches:
            existing = matches[0]
            expected = {
                "id": event_id, "technique_id": proposal["technique_id"],
                "from_state": proposal["from_state"], "to_state": proposal["to_state"],
                "effective_date": proposal["effective_date"],
                "evidence_ids": proposal["evidence_ids"],
                "ruleset_version": RULESET,
                "approval_key": key, "approved": True,
                "applied_revision": proposal["state_revision"] + 1,
            }
            if len(matches) == 1 and existing == expected:
                return None, {"result": "already-applied", "state_revision": state["revision"], "event_id": event_id}
            raise ValueError("conflicting progression event")
        if type(proposal["state_revision"]) is not int or state["revision"] != proposal["state_revision"]:
            raise ValueError("stale state revision")
        digest = "sha256:" + hashlib.sha256(canonical(state)).hexdigest()
        if digest != proposal["state_digest"]:
            raise ValueError("state content changed without revision update")
        # An approved transition is a present-tense state change, not a
        # historical query. Refuse to bypass later approved feedback by
        # backdating the effective date; allow read-only historical evaluate.
        exercise_owners = {e["id"]: e["technique_id"] for e in catalog["exercises"]}
        latest_observation = max(
            (_iso(s["date"]) for s in state["sessions"]
             if s["approved"] and
             exercise_owners[s["exercise_id"]] == proposal["technique_id"]),
            default=None,
        )
        if latest_observation is not None and _iso(proposal["effective_date"]) < latest_observation:
            raise ValueError("backdated transition ignores later approved practice feedback")
        # Recalculate the gate under the lock, on exact current contents.
        verified = evaluate(catalog, state, proposal["technique_id"],
                            proposal["to_state"], proposal["effective_date"])
        if verified != proposal:
            raise ValueError("progression gate changed since review")
        event = {
            "id": event_id, "technique_id": proposal["technique_id"],
            "from_state": proposal["from_state"], "to_state": proposal["to_state"],
            "effective_date": proposal["effective_date"],
            "evidence_ids": proposal["evidence_ids"],
            "ruleset_version": RULESET, "approval_key": key, "approved": True,
            "applied_revision": state["revision"] + 1,
        }
        next_state = {**state, "revision": state["revision"] + 1,
                      "progression_events": [*state.get("progression_events", []), event]}
        validate_state(next_state, catalog)
        validate_events(next_state, catalog)
        return next_state, {"result": "applied", "state_revision": next_state["revision"],
                            "event_id": event_id}
    return transact(path, update)


def maintenance_due(catalog: dict, state: dict, as_of: str, interval_days: int) -> list[dict]:
    validate_catalog(catalog)
    validate_state(state, catalog)
    validate_events(state, catalog)
    day = _iso(as_of)
    if type(interval_days) is not int or not 1 <= interval_days <= 365:
        raise ValueError("maintenance interval days must be 1..365")
    results = []
    for technique in sorted(_technique_ids(catalog)):
        current, approved_on = current_state(state, technique)
        if current != "maintained":
            continue
        # Verified post-promotion context checks may refresh last verification.
        reference = _iso(approved_on)
        previous_event = next(
            (e for e in reversed(state.get("progression_events", []))
             if e["technique_id"] == technique), None
        )
        records = _eligible_feedback(
            state, catalog, technique, day, reference,
            previous_event["applied_revision"] if previous_event else None
        )
        verified = [e for e in records
                    if e["context"] == "musical-context"
                    and e["passed"] is True and e["comfort"] == "comfortable"]
        last = max([reference, *(_iso(e["date"]) for e in verified)])
        due_on = last + timedelta(days=interval_days)
        adverse = [e for e in records if
                   e["passed"] is False or e["comfort"] == "tension"
                   or e["feedback"] == "hard"]
        latest_adverse = max((_iso(e["date"]) for e in adverse), default=None)
        needs_recovery = latest_adverse is not None and latest_adverse >= last
        if day >= due_on or needs_recovery:
            results.append({
                "technique_id": technique, "last_verified": last.isoformat(),
                "due_date": due_on.isoformat(), "overdue_days": max(0, (day-due_on).days),
                "reason": "adverse-feedback" if needs_recovery else "maintenance-due"
            })
    return sorted(results, key=lambda item: (item["due_date"], item["technique_id"]))
