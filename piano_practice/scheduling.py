"""Deterministic goal-weighted, age-sensitive focus recommendations.

This is a read-only scheduling policy. It does not create practice events,
authorize proficiency changes or assume unobserved experience.
"""
from __future__ import annotations

from datetime import date


def weighted_focus(techniques: list[str], active: list[dict],
                   by_id: dict[str, dict], on_date: str,
                   weights: dict[str, int] | None) -> tuple[str, dict]:
    """Return recommended technique and an inspectable score breakdown.

    Legacy configurations without goal_weights preserve the previous
    least-recently-approved behavior.
    """
    if not techniques or len(techniques) != len(set(techniques)):
        raise ValueError("invalid technique order")
    if weights is not None:
        if not isinstance(weights, dict) or set(weights) != set(techniques):
            raise ValueError("goal_weights must cover exactly configured technique IDs")
        if any(type(value) is not int or not 1 <= value <= 5
               for value in weights.values()):
            raise ValueError("goal weights must be integer 1..5")
    last_by = {}
    for technique in techniques:
        history = [s["date"] for s in active
                   if by_id[s["exercise_id"]]["technique_id"] == technique]
        last_by[technique] = max(history, default=None)

    if weights is None:
        focus = min(techniques, key=lambda t: (last_by[t] or "", techniques.index(t)))
        return focus, {
            "policy": "least-recent-approved/v1",
            "candidate_scores": [],
            "chosen": focus,
        }

    day = date.fromisoformat(on_date)
    earliest = min((date.fromisoformat(s["date"]) for s in active), default=day)
    candidates = []
    for technique in techniques:
        prior = last_by[technique]
        days = ((day - date.fromisoformat(prior)).days + 1 if prior is not None
                else (day - earliest).days + 2)
        days = max(1, days)
        weight = weights[technique]
        candidates.append({
            "technique_id": technique,
            "weight": weight,
            "days_since_last": days if prior is not None else None,
            "unpracticed_age": days if prior is None else None,
            "last_approved_date": prior,
            "score": days * weight,
        })
    chosen_index = max(range(len(candidates)), key=lambda i: (
        candidates[i]["score"], -i
    ))
    return techniques[chosen_index], {
        "policy": "weighted-staleness/v1",
        "candidate_scores": candidates,
        "chosen": techniques[chosen_index],
    }


def warmups_for_prepare(config: dict, allowed: set[str],
                        prepare_minutes: int) -> list[dict]:
    rows = config.get("warmups", [])
    if not isinstance(rows, list) or len(rows) > 4:
        raise ValueError("warmups must be a list of at most four entries")
    seen = set()
    total = 0
    result = []
    for row in rows:
        if not isinstance(row, dict) or set(row) != {"technique_id", "minutes", "prompt"}:
            raise ValueError("invalid warmup specification")
        technique = row["technique_id"]
        minutes = row["minutes"]
        prompt = row["prompt"]
        if (technique not in allowed or technique in seen
                or type(minutes) is not int or minutes < 1
                or not isinstance(prompt, str) or not 1 <= len(prompt) <= 200):
            raise ValueError("invalid warmup technique, duration, or prompt")
        seen.add(technique)
        total += minutes
        result.append(dict(row))
    if total > prepare_minutes:
        raise ValueError("warmups exceed already-allocated prepare minutes")
    return result


def reviewed_context(active: list[dict], by_id: dict[str, dict],
                     technique_id: str) -> list[dict]:
    """Only replay already approved references; do not infer completion."""
    candidates = [s for s in active
                  if by_id[s["exercise_id"]]["technique_id"] == technique_id
                  and (s.get("method_book_id") is not None
                       or s.get("repertoire_id") is not None)]
    if not candidates:
        return []
    # Equal-date tie: later approval revision wins when present.
    source = max(candidates, key=lambda s: (
        s["date"], s.get("applied_revision", 0)
    ))
    ref = {
        "source_event_id": source.get("id"),
        "source_practice_date": source["date"],
        "status": "previously-referenced; completion unknown",
    }
    if source.get("method_book_id") is not None:
        ref["method_book_id"] = source["method_book_id"]
        ref["method_checkpoint"] = source.get("method_checkpoint")
    if source.get("repertoire_id") is not None:
        ref["repertoire_id"] = source["repertoire_id"]
    return [ref]
