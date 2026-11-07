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
| `feedback/v2` | `pianoctl feedback propose --context ...` | Explicit `isolation` or `musical-context`, human `observation`, optional `repertoire_id`, source-state and catalog digests, content acknowledgement |
| `progression/v1` | `pianoctl progression evaluate/apply` | Bounded multi-session gate proposal and distinct explicit approval; one-step regression and maintained-state maintenance queue |
| `midi-trace-inspection/v1` | `pianoctl hardware <take>` | Structural diagnostic from provided MIDI bytes; **never physical device attestation** |
| Original MusicXML | `pianoctl notation --exercise ...` | Original single-staff exercise generated from public note sequences; no imported Alfred notation |

## Authority, integrity and uncertainty

The state moves only through explicit, reviewed `feedback apply` or `progression apply` operations, never through `plan`, MIDI scores, or calendar metadata. Each accepted event increments a state revision; exact repeated proposals are idempotent, and stale/conflicting event IDs or altered source contents are rejected. Separate writers must honor the same POSIX sidecar lock. SHA-256 acknowledgement keys bind reviewed *content*, **not user authentication/signature or multi-user authorization**.

`feedback/v2` is required to establish isolation/musical-context competency gates. The player supplies difficulty/comfort and whether the task was accomplished; a MIDI result cannot supply fingering, staff comprehension, hand identity, physical comfort or acoustic performance. Missing evidence remains `unknown` or `blocked`, not guessed.

Technique states: `discovered → developing → reliable-isolation → reliable-context → maintained`. Reviewable lifecycle states `paused` and `retired` are vocabulary only, not part of the v1 transition writer. A one-step regression needs explicit adverse evidence. Positive gate requirements are based on distinct approved practice dates after the previous transition and latest adverse feedback.

The content catalogs are intended as public synthetic/reference resources. Actual practice history, recordings, MIDI takes, and score page tracking are private and ignored under `local/`. Do not ship copyrighted method-book material into either public fixtures or generated files.

See [progression semantics](../../docs/progression.md), [curriculum references](../../docs/curriculum.md), and [Oxygen Pro 61 qualification](../../docs/hardware/qualification.md).
