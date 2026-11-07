# Piano practice contracts

Contracts are local-first and machine-readable JSON. Preserve compatibility by adding versioned contracts instead of silently changing existing meanings.

## Core records

| Contract | Source | Semantic boundary |
| --- | --- | --- |
| `catalog/v1` | `catalogs/exercises.json` | Stable exercise ID, technique, level (0/1), MIDI note sequence, tempo, subdivision, instructions, self-check; optional `assessment_mode: human` prevents MIDI-only pass claims |
| `curriculum/v1` | `catalogs/curriculum.json` | Method-book references, technique goals, recital **metadata** only; no text/notation from copyrighted materials |
| `practice-config/v1` | `config/practice.json` | IANA timezone, preferred days/time, focus order, 15/20/30-minute session size, maintained-state verification interval; **not a notification service** |
| `state/v1` | `examples/learner-state.json` | Revision, approved feedback sessions, optional append-only approved `progression_events`; real state belongs in ignored `local/` |
| `session/v1` | `pianoctl plan` | Read-only deterministic session proposal bound to source state revision |
| `midi-take/v1` | `pianoctl capture` | Timestamped MIDI note-on/off and sustain CC64, MIDI channel, pitch and velocity; no audio or finger identity |
| `assessment/v1` | `pianoctl assess` | Relative onset/pitch/release/dynamics evidence, not mastery; manual-requirement returns `unknown` for physical/reading techniques |
| `feedback/v1` | `pianoctl feedback propose` (without context) | Historical reviewed self-report record; valid for schedule history, **ineligible** for context-specific competency gates |
| `feedback/v2` | `pianoctl feedback propose --context ...` | Explicit `isolation` or `musical-context`, named IANA `timezone`, human `observation`, optional `repertoire_id`, `method_book_id` and private `method_checkpoint`, source-state and catalog digests, content acknowledgement |
| `progression/v1` | `pianoctl progression evaluate/apply` | Bounded multi-session gate proposal and distinct explicit approval; one-step regression and maintained-state maintenance queue |
| `midi-trace-inspection/v1` | `pianoctl hardware <take>` | Structural diagnostic from provided MIDI bytes; **never physical device attestation** |
| Original MusicXML | `pianoctl notation --exercise ...` | Original single-staff exercise generated from public note sequences; no imported Alfred notation |
| PianGo MusicXML | `pianoctl export --target piango --exercise ...` | Deterministic original-score export of all 22 catalog drills; model-specific two-hand timelines, authored enharmonic spellings, optional *illustrative* printed fingerings. Import and observed technique remain unverified |

## Authority, integrity and uncertainty

The state moves only through explicit, reviewed `feedback apply` or `progression apply` operations, never through `plan`, MIDI scores, or calendar metadata. Approved session history is capped at 10,000 records and progression history at 10,000 events; the system fails closed at capacity and does not silently prune older evidence. Session event IDs must be unique when present, while legacy records without IDs remain readable. Each accepted event increments a state revision; exact repeated proposals are idempotent, and stale/conflicting event IDs or altered source contents are rejected. Separate writers must honor the same POSIX sidecar lock. SHA-256 acknowledgement keys bind reviewed *content*, **not user authentication/signature or multi-user authorization**.

`feedback/v2` is required to establish isolation/musical-context competency gates. The player supplies difficulty/comfort and whether the task was accomplished; a MIDI result cannot supply fingering, staff comprehension, hand identity, physical comfort or acoustic performance. Missing evidence remains `unknown` or `blocked`, not guessed.

Each approved feedback/v2 and progression event carries its `applied_revision` so an adverse report added after a transition on the same calendar date is still available for recovery checks. Same-day positive evidence does not count as a new independent practice date. Exact-event replays must match the original append revision.

Technique states: `discovered → developing → reliable-isolation → reliable-context → maintained`. Reviewable lifecycle states `paused` and `retired` are vocabulary only, not part of the v1 transition writer. A one-step regression needs explicit adverse evidence. Positive gate requirements are based on distinct approved practice dates after the previous transition and latest adverse feedback. An explicitly `hard` report cannot support a positive gate, even when the player also reports `passed=true`. Applying a historical proposal refuses backdating behind later approved practice observations for the same technique.

The content catalogs are intended as public synthetic/reference resources. Actual practice history, recordings, MIDI takes, and score page tracking are private and ignored under `local/`. Do not ship copyrighted method-book material into either public fixtures or generated files.

See [progression semantics](../../docs/progression.md), [curriculum references](../../docs/curriculum.md), and [Oxygen Pro 61 qualification](../../docs/hardware/qualification.md).


### Onset-group extensions

`onset-groups/v1` is an optional catalog realization containing ordered
`onsets`, each with `pitches` and aligned intended `hands` values
(`left`/`right`). The flattened sequence must match the existing
`catalog/v1` note order or validation fails; absent realization means one
note per onset. `session/v1` includes the normalized realization as advisory
metadata. `assessment/v1` adds a `within_group_sync` check and timing
metrics for group starts while retaining its original pitch/lifecycle
checks. Two-handed exercise results still carry an unknown required human
observation and can never autonomously approve proficiency.


An `onset-groups/v1` realization may additionally contain bounded, contiguous
`phases` (named start/end beat indices) and optional `finger_cues`
(intended hand, onset index, finger 1–5, descriptive label). Each cue must
reference an actually present note for that intended hand; duplicate cues,
unknown hands, out-of-range fingers and gapped phases fail catalog validation.
These are instructional references, **never sensed fingering**. The five-phase
C-major scale arrangement and LH finger 3/4 crossing cues are explicitly
provisional player-provided goals, not qualified physical evidence.


A legacy one-note-per-onset session may report `hands: [null]` to
preserve **unspecified** hand identity. In an explicit simultaneous pair, both
intended roles must be named distinctly `left` and `right`.
MIDI timing and within-group synchronization are `unknown` (not passing)
when any extra onset remains unmatched after consuming the expected groups.

### Optional weighted scheduling

`practice-config/v1` may specify `goal_weights`: one integer weight 1–5
for each configured technique, and `warmups`: a bounded set of prompts whose
durations fit **within** `session/v1`'s prepare allocation. Missing
`goal_weights` preserves legacy least-recent scheduling. The weighted policy
(`weighted-staleness/v1`) multiplies explicit user weights by elapsed days
from last approved practice (with an increasing age for not-yet-practiced
techniques). It exposes a per-candidate score breakdown. Adverse recovery
precedence and explicit manual `--focus` are transparent; manual override
carries a warning when it defers recovery.

`session/v1` also includes reviewed `previous_context_references` to
already-identified method-book or recital milestones; they are not proof of
completion or a license to reproduce source sheets. Weighted planning does
not mutate learner state, approve competency, or allocate more minutes than
configured.

