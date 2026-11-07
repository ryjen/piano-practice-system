# Deterministic progression, evidence, and maintenance

The public piano core borrows the guitar-practice-system boundary: **evidence → assessment proposal → explicit approval → scheduling**. Proposals are reproducible and **do not mutate learner state**.

## Feedback/v2

Use `pianoctl feedback propose` with `--context isolation` or `--context musical-context`, `--timezone America/Vancouver`, and `--observation`. Optional `--method-book-id alfred-basic-adult-1` / `--method-checkpoint "Level One section 3"` record the user's private method-book milestone without copying any copyrighted notation. Both the pass/fail/unknown self-check and physical comfort must be reported by the player; no MIDI score can claim these observations.

Example (from a genuine practice session, with private state initialized):

```sh
python3 -m piano_practice.cli feedback propose \
  --state local/learner-state.json --id reading-nov10-a \
  --date 2026-11-10 --exercise reading-staff-steps --bpm 60 \
  --feedback appropriate --comfort comfortable --passed yes \
  --context isolation --observation "Read each note before playing" \
  > local/reading-nov10-proposal.json

# Review the full JSON, then explicitly supply the exact approval_key.
python3 -m piano_practice.cli feedback apply local/reading-nov10-proposal.json \
  --state local/learner-state.json \
  --acknowledge 'sha256:REPLACE_WITH_REVIEWED_KEY'
```

For recital application, supply `--context musical-context --repertoire-id fur-elise`, `over-the-rainbow`, or `jacobs-ladder`. Only metadata and user-authored observations are stored. The CLI does **not** import sheet music from Alfred.

Legacy `feedback/v1` events without explicit context remain valid history for scheduling, but **cannot satisfy competency-transition gates**.

## Ordered, approval-gated competency

| Transition | Required current evidence since preceding approved transition |
| --- | --- |
| discovered → developing | 1 approved, comfortable, passed feedback/v2 session in any context |
| developing → reliable-isolation | 2 separate approved, comfortable, passed isolation dates |
| reliable-isolation → reliable-context | 2 separate approved, comfortable, passed musical-context dates |
| reliable-context → maintained | 2 additional separate approved, comfortable, passed musical-context dates |
| one-step regression | At least one explicit adverse feedback/v2 event since preceding transition, separately approved |

An adverse observation (`passed=false`, `comfort=tension`, or `feedback=hard`) **resets forward repeatability gates**. A hard difficulty report is adverse even when `passed=true` and comfort is reported comfortable. Historical validation rejects attempts to use it as positive competency evidence. A same-date adverse report that was **approved after** an existing transition is included in recovery/maintenance checks by comparing stored `applied_revision` values. Same-day successes are deliberately excluded from the next stage's distinct-date promotion evidence. Earlier successes cannot be reused to promote immediately after a failure. Missing/unknown fields remain unknown, and one best take cannot prove maintenance. The gate is based on reviewed player observations, not on an independent exam or posture analysis.

```sh
pianoctl progression evaluate \
  --technique reading --target developing \
  --date 2026-11-12 --state local/learner-state.json \
  > local/reading-progression-proposal.json

# Only when gate==pass, review it and apply with the exact key.
pianoctl progression apply local/reading-progression-proposal.json \
  --state local/learner-state.json \
  --acknowledge 'sha256:REPLACE_WITH_REVIEWED_KEY'
```

Progression approval persists an append-only event, checks expected source revision and canonical content digests under a cooperative POSIX lock, rejects stale or conflicting transitions, and uses atomic state replacement. The read-only gate may evaluate a past date, but approval refuses a backdated transition that would disregard any newer approved practice feedback for the same technique. Exact replay reports `already-applied`; the approval key is a *content acknowledgement*, **not** identity proof or a digital signature. Out-of-band editors ignoring the lock violate the single-user concurrency contract.

## Maintenance queue

Only `maintained` techniques appear. The configured cadence defaults to 14 days from the last approved maintained-state transition or subsequent comfortable musical-context verification. A newer adverse musical-context report makes recovery due immediately rather than allowing a misleading maintenance-green state.

```sh
pianoctl progression due --date 2026-11-25 \
  --state local/learner-state.json

pianoctl plan --date 2026-11-25 \
  --state local/learner-state.json
```

The planner prioritizes due maintenance before ordinary technique rotation. Calendar notifications and unattended runs are not installed. The player may choose to simplify or stop at any time.

## Repository boundaries

Practice history, recitals, recording references and inferred capability details are personal. Store actual state under ignored `local/`, never in public examples. No AI inference, hosted account, or external service is required.

See [curriculum](curriculum.md), [Oxygen hardware qualification](hardware/qualification.md), and [contracts](../contracts/v1/README.md).
