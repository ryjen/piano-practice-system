# Goal-weighted practice scheduling (optional)

The system starts with a user-authored goal map, not inferred skill levels.
The default configuration gives additional attention to **sheet reading (4)**,
**two-hand coordination (4)**, **arpeggios (3)**, and
**scale choreography (3)**. Other technique weights are lower (1–2).
The numbers are priorities, not competence ratings.

## Selection contract

For each technique, the planner considers only approved sessions dated on or
before the requested session date. The weight must be an integer 1–5 for
**every** configured technique; invalid or unknown IDs fail closed.

- Previously practiced: score = weight × (calendar days since most recent
  approved session + 1).
- Never practiced: score = weight × (calendar days since earliest approved
  practice + 2); if no history, the requested date is used as the epoch.
- Highest score wins. Ties follow the explicit `technique_order`.
- Maintained-state recovery after adverse feedback takes priority over routine
  overdue verification, and both precede weighted preference selection.
- A deliberate `--focus TECHNIQUE` override wins over the suggestion,
  but emits a warning when it defers a recovery/maintenance obligation.
- No scheduling choice changes the player's state, success evidence, or
  competency. An additional state transition always requires explicit review.

Without `goal_weights`, the old least-recently-practiced policy remains
available, making adoption opt-in at the configuration level. Source state
and injected date fully determine the plan; no time service or hosted model
is needed.

## Bounded preparation, not extra session time

`warmups` are optional short prompts (one minute of reading and one minute
of two-hand coordination in the default config). They are **inside** the
original `prepare` stage and must not exceed its allocated minutes.
They are not a second primary technique or an automatically verified task.

## Reviewed Alfred and recital context

`previous_context_references` may refer back to a previously approved
feedback/v2 `method_book_id`, short personal `method_checkpoint`, or
`repertoire_id` for the selected technique. They always carry
`status: previously-referenced; completion unknown`. Actual books, private
page references, and recorded notes remain under ignored `local/`.

This deliberately does **not** infer:
- completion of Alfred Level One or readiness to move into Level Two;
- successful reading of a score from correct MIDI pitches;
- readiness for a recital from a single successful take;
- hand or finger identity from the USB keyboard.

## Deterministic example

Run `pianoctl plan --date 2026-11-10 --state local/learner-state.json`.
The proposal includes `selection.candidate_scores` with each technique's
weight, approved-practice age, score, and choice, plus the selected exercise.

A synthetic 4-week, twice-weekly simulation with 11 techniques yields
reading **3** times, coordination **2**, arpeggios **1**,
scale-patterns **1**, and minor **1**. It represents scheduling policy, not
a promised learning outcome. A 36-week synthetic regression validates eventual
coverage of all lower-weight subjects as recency pressure accumulates.

## Operational limitations

With only two primary sessions per week, all 11 techniques cannot appear
every four weeks. The default weights intentionally prioritize reading and
hands-together practice; low-weight techniques take longer to recur.
Adjust weights deliberately when repertoire, physical comfort or goals
change, and review the generated priority scores.

Stop or simplify practice for discomfort. No silent mastery, recurring
notifications, calendar writes, auto-uploaded recordings, or paid integrations.
