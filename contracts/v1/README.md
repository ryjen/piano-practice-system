# Exchange contracts v1

The public JSON contracts and their semantics are stable for this reference slice.

- `catalogs/exercises.json`: `schema_version: 1`; entries have stable `id`, `technique_id`, `level` (0/1), `title`, `notes` (MIDI integers), `bpm`, `subdivision` (1/2 events per quarter note), optional `dynamics: alternate`, instructions, and self-check.
- `config/practice.json`: explicit timezone and preference, duration 15/20/30, ordered technique IDs. Preferred days/time are only metadata; no background scheduler is installed.
- `examples/learner-state.json`: `schema_version: 1`, monotonically increased `revision`, and `sessions` entries. Each session requires `date`, `exercise_id`, `feedback` (`easy|appropriate|hard`), `comfort` (`comfortable|tension|unknown`), `passed` (`true|false|null`), and explicit `approved` boolean.
- `midi-take/v1`: `exercise_id`, `events` with relative monotonic `t_ms`, MIDI channel 0–15; note-on/off includes pitch 0–127 and velocity 0–127; CC64 uses `control:64,value:0..127`. A zero-velocity note-on is semantically a note-off.
- `session/v1`: advisory proposal with a state revision, realization, stages, safety and provenance fields. Never treated as an approved schedule.
- `assessment/v1`: advisory per-check outcomes `pass|fail|unknown|not-applicable`, diagnostic numbers and known limitations; **not** a canonical learning-state event.

Absence of a MIDI take means not measured; absence of physical self-report means comfort unknown. Neither implies failure or success.

No scheduler-generated date or extra device events are treated as evidence. JSON fixtures are synthetic. Stable IDs must not be reused for semantically different exercises. For v2 changes, add a version and fixtures rather than silently changing v1 behavior.
