"""Explicit review-and-approval ledger for local piano practice.

This module does not infer proficiency or promote canonical mastery states.
Only a deliberate apply call can persist an approved feedback event.
"""
from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path, PurePosixPath
import re
import tempfile
from datetime import date
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

try:
    import fcntl
except ImportError:  # The read-only planner remains usable on Windows.
    fcntl = None

from .core import COMFORT, FEEDBACK, validate_catalog, validate_state

IDENTIFIER = re.compile(r"^[a-z0-9][a-z0-9-]{0,95}$")
SESSION_FIELDS = ("id", "date", "exercise_id", "feedback", "comfort", "passed", "realized_bpm", "evidence_refs")


def canonical(value: dict) -> bytes:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=True,
                      allow_nan=False).encode("utf-8")


def _identifier(value: object, label: str) -> None:
    if not isinstance(value, str) or not IDENTIFIER.fullmatch(value):
        raise ValueError(f"invalid {label}: expected stable lowercase kebab-case id")


def _event(event: dict, catalog: dict) -> None:
    base = set(SESSION_FIELDS)
    extended = base | {"context", "observation", "repertoire_id",
                       "timezone", "method_book_id", "method_checkpoint"}
    if not isinstance(event, dict) or set(event) not in (base, extended):
        raise ValueError("invalid feedback event fields")
    if set(event) == extended:
        if event["context"] not in ("isolation", "musical-context"):
            raise ValueError("feedback/v2 requires explicit practice context")
        if not isinstance(event["observation"], str) or len(event["observation"]) > 2000:
            raise ValueError("invalid practice observation")
        if event["repertoire_id"] is not None:
            _identifier(event["repertoire_id"], "repertoire id")
        if not isinstance(event["timezone"], str) or "/" not in event["timezone"]:
            raise ValueError("feedback/v2 needs a named IANA timezone")
        try:
            ZoneInfo(event["timezone"])
        except (ZoneInfoNotFoundError, ValueError) as exc:
            raise ValueError("invalid IANA timezone") from exc
        if event["method_book_id"] is not None:
            _identifier(event["method_book_id"], "method book id")
        checkpoint = event["method_checkpoint"]
        if checkpoint is not None:
            if event["method_book_id"] is None or not isinstance(checkpoint, str) or not 1 <= len(checkpoint) <= 120:
                raise ValueError("checkpoint requires a method book id and short private reference")
    _identifier(event["id"], "feedback id")
    try:
        parsed = date.fromisoformat(event["date"])
        if parsed.isoformat() != event["date"]:
            raise ValueError("non-canonical date")
    except (ValueError, TypeError) as exc:
        raise ValueError("invalid feedback ISO date") from exc
    if event["exercise_id"] not in {x["id"] for x in catalog["exercises"]}:
        raise ValueError("unknown exercise")
    if event["feedback"] not in FEEDBACK or event["comfort"] not in COMFORT:
        raise ValueError("invalid feedback or physical comfort")
    if event["passed"] is not None and type(event["passed"]) is not bool:
        raise ValueError("passed must be true, false, or unknown")
    if type(event["realized_bpm"]) is not int or not 40 <= event["realized_bpm"] <= 180:
        raise ValueError("invalid realized_bpm")
    refs = event["evidence_refs"]
    if not isinstance(refs, list) or len(refs) > 16:
        raise ValueError("invalid evidence references")
    for ref in refs:
        if not isinstance(ref, str) or not 1 <= len(ref) <= 256:
            raise ValueError("invalid evidence reference")
        p = PurePosixPath(ref)
        if p.is_absolute() or ".." in p.parts or "\\" in ref or ":" in ref:
            raise ValueError("evidence reference must be a safe, relative local path")
    if len(refs) != len(set(refs)):
        raise ValueError("duplicate evidence reference")


def proposal(catalog: dict, state: dict, *, event_id: str, on_date: str,
             exercise_id: str, feedback: str, comfort: str,
             passed: bool | None, realized_bpm: int, evidence_refs: list[str] | None = None,
             context: str | None = None, observation: str = "",
             repertoire_id: str | None = None, timezone: str = "America/Vancouver",
             method_book_id: str | None = None,
             method_checkpoint: str | None = None) -> dict:
    validate_catalog(catalog)
    validate_state(state, catalog)
    event = dict(id=event_id, date=on_date, exercise_id=exercise_id,
                 feedback=feedback, comfort=comfort, passed=passed,
                 realized_bpm=realized_bpm, evidence_refs=list(evidence_refs or []))
    if context is None and (observation or repertoire_id is not None
                            or method_book_id is not None or method_checkpoint is not None):
        raise ValueError("feedback/v2 context is required for observations or materials")
    version = "feedback/v1"
    if context is not None:
        version = "feedback/v2"
        event.update(context=context, observation=observation,
                     repertoire_id=repertoire_id, timezone=timezone,
                     method_book_id=method_book_id,
                     method_checkpoint=method_checkpoint)
    _event(event, catalog)
    bare = dict(
        record_type="feedback-proposal", contract_version=version,
        state_revision=state["revision"],
        state_digest="sha256:" + hashlib.sha256(canonical(state)).hexdigest(),
        catalog_digest="sha256:" + hashlib.sha256(canonical(catalog)).hexdigest(),
        event=event
    )
    return {**bare, "approval_key": "sha256:" + hashlib.sha256(canonical(bare)).hexdigest()}


def _validate_proposal(proposed: dict, catalog: dict) -> str:
    if not isinstance(proposed, dict) or set(proposed) != {
        "record_type", "contract_version", "state_revision", "state_digest",
        "catalog_digest", "event", "approval_key"
    }:
        raise ValueError("invalid feedback proposal")
    if proposed["record_type"] != "feedback-proposal" or proposed["contract_version"] not in ("feedback/v1", "feedback/v2"):
        raise ValueError("unsupported proposal version")
    expected_fields = set(SESSION_FIELDS)
    if proposed["contract_version"] == "feedback/v2":
        expected_fields.update((
            "context", "observation", "repertoire_id", "timezone",
            "method_book_id", "method_checkpoint"
        ))
    if set(proposed["event"]) != expected_fields:
        raise ValueError("proposal event does not match version")
    if type(proposed["state_revision"]) is not int or proposed["state_revision"] < 0:
        raise ValueError("invalid state revision")
    _event(proposed["event"], catalog)
    if proposed["catalog_digest"] != "sha256:" + hashlib.sha256(canonical(catalog)).hexdigest():
        raise ValueError("catalog changed since feedback proposal")
    bare = {k: v for k, v in proposed.items() if k != "approval_key"}
    expected = "sha256:" + hashlib.sha256(canonical(bare)).hexdigest()
    if proposed["approval_key"] != expected:
        raise ValueError("proposal content/key mismatch")
    return expected


def apply(path: Path | str, catalog: dict, proposed: dict, acknowledged_key: str) -> dict:
    """Apply one explicit approval with a POSIX lock, atomic replace, and replay protection.

    The content hash is only a human review acknowledgement, not a signature.
    """
    validate_catalog(catalog)
    expected = _validate_proposal(proposed, catalog)
    if acknowledged_key != expected:
        raise ValueError("approval key does not match reviewed proposal")
    if fcntl is None:
        raise RuntimeError("feedback apply requires POSIX fcntl locking (Linux/macOS)")
    target = Path(path)
    if target.is_symlink() or not target.is_file():
        raise ValueError("state must be an existing regular non-symlink file")
    # The lock file is a stable sibling; do not use it for canonical data.
    lock_path = target.with_name(target.name + ".lock")
    if lock_path.is_symlink():
        raise ValueError("lock path must not be a symlink")
    with open(lock_path, "a+b") as lock:
        fcntl.flock(lock.fileno(), fcntl.LOCK_EX)
        if target.is_symlink() or not target.is_file():
            raise ValueError("state file changed during approval")
        with open(target, encoding="utf-8") as source:
            state = json.load(source)
        validate_state(state, catalog)
        event = proposed["event"]
        prior = [x for x in state["sessions"] if x.get("id") == event["id"]]
        if prior:
            exact_entry = {**event, "approved": True, "approval_key": expected}
            if proposed["contract_version"] == "feedback/v2":
                exact_entry["applied_revision"] = proposed["state_revision"] + 1
            # A stored hash/ID is not sufficient: compare the complete approved
            # event to reject edits that preserve the original approval key.
            if len(prior) == 1 and prior[0] == exact_entry:
                return {"result": "already-applied", "state_revision": state["revision"],
                        "event_id": event["id"]}
            raise ValueError("conflicting feedback event id")
        if proposed["state_revision"] != state["revision"]:
            raise ValueError("stale state revision; generate a new proposal")
        digest = "sha256:" + hashlib.sha256(canonical(state)).hexdigest()
        if proposed["state_digest"] != digest:
            raise ValueError("state changed without revision update; generate a new proposal")
        # Existing records without IDs remain readable for compatibility.
        updated = dict(state)
        updated["revision"] = state["revision"] + 1
        approved_entry = {**event, "approved": True, "approval_key": expected}
        if proposed["contract_version"] == "feedback/v2":
            approved_entry["applied_revision"] = updated["revision"]
        updated["sessions"] = [*state["sessions"], approved_entry]
        validate_state(updated, catalog)
        # A partial/corrupt write must not replace canonical state.
        temp_path = None
        try:
            with tempfile.NamedTemporaryFile(mode="w", encoding="utf-8",
                    dir=target.parent, prefix=".piano-state-", suffix=".tmp",
                    delete=False) as output:
                temp_path = Path(output.name)
                json.dump(updated, output, sort_keys=True, indent=2)
                output.write("\n")
                output.flush()
                os.fsync(output.fileno())
            os.chmod(temp_path, 0o600)
            if target.is_symlink():
                raise ValueError("state changed to symlink during approval")
            os.replace(temp_path, target)
            temp_path = None
            directory_fd = os.open(target.parent, os.O_RDONLY)
            try:
                os.fsync(directory_fd)
            finally:
                os.close(directory_fd)
        finally:
            if temp_path is not None:
                temp_path.unlink(missing_ok=True)
        return {"result": "applied", "state_revision": updated["revision"],
                "event_id": event["id"]}
