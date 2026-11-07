# Roadmap and acceptance boundaries

## Implemented (software reference)

- Technique-first catalog with **eleven focus areas** and 22 bounded exercises: staff reading, two-handed coordination, fourths/fifths, triads, minor/accidentals, four-note harmony, arpeggios, personal two-hand scale patterns, pulse, navigation, dynamics
- Alfred's Basic Adult Piano Course Levels 1 and 2 as method-book *references*, not reproduced content
- Recital *metadata* for Für Elise, Over the Rainbow, and Jacob's Ladder; arrangement and page progress unknown
- Explicit Tuesday/Thursday planning preference, injected-date deterministic technique rotation, 15/20/30-minute plans, five-block flow and five-minute fallback
- Original single-staff MusicXML reading/minor exercises; no copyrighted book content or arbitrary external song transcription
- Optional MIDI capture using mido/python-rtmidi, offline pitch/timing/release/relative-velocity assessment, human-required gate for reading and physical techniques
- Versioned `feedback/v1` compatibility and `feedback/v2` explicit isolation/musical-context observations, named timezone, private Alfred checkpoint and optional recital reference; append revision preserves same-day recovery evidence
- Explicit feedback approval and deterministic competency progression with state/content digests, stale-state and conflicting-event rejection, one-step review-only regression, replay idempotence, cooperative POSIX lock and atomic state replacement
- Distinct-day gate evidence, adverse-feedback reset, maintained-state scheduling with explicit due/recovery reasons
- MIDI trace inspection with synthetic positive/negative tests that **never** assert physical hardware qualification

## Remaining external acceptance — do not mark done without evidence

1. **Oxygen Pro 61 physical qualification (#2):** real USB/ALSA MIDI port, known key-to-note calibration, CC64, channel/octave behavior, disconnect and reconnect, and independent DAW view on actual hardware. The remote Desktop Commander container has **no /dev/snd**, so this must be run on the connected host/device.
2. **Independent PR review and exact-head CI:** qualify implementation commit, adjudicate all review findings, and merge only when required checks are green. After merge, verify `main` CI and code/docs reflect final state.

## Subsequent enhancements (not part of current milestone)

- True hands-together/dual-staff notation and synchronized metronome/DAW timing
- Context-specific score-reading assessments using user-authored evidence beyond the single-staff seed exercises
- More expressive voicings, key signatures, pedal semantics, modes and rhythm patterns
- Optional local playback UI and audio via an external synthesizer
- Calendar/iCalendar integration and explicit longer-term learning capacity limits
- Read-only repertoire section planning with private checkpoint IDs instead of copyrighted scores

## Non-goals

Hosted subscriptions, mandatory AI services, uploading private practice logs, automatic injury/fingering diagnosis, automatic mastery claims from MIDI, copyrighted Alfred reproductions, or unapproved remote device changes.


### Personal technique follow-up

The clarified five-phase movement is represented in C major, including **both-hand returns** for the contrary-motion phases 2 and 4. Physical starting octaves (illustratively LH C3 / RH C4), exact five-phase fingering and ergonomic suitability still require direct player/teacher confirmation. LH finger 3 on A3 and 4 on D4 remain separate, explicitly user-reported cues in the two-octave scale drill. Neither score nor phase metadata detects fingers. Transposition to other keys and validated finger-specific recommendations remain opt-in later enhancements.


### Goal-weighted planner (software)

An optional bounded `goal_weights` map is evaluated against approved session recency. The planner remains read-only and returns an inspectable score/rationale, uses in-budget reading/coordination warm-ups, accepts an explicit `--focus` override with a deferred-recovery warning, and replays private reviewed Alfred/repertoire checkpoints without claiming completion. Legacy config without weights still rotates by least recent technique. All dates remain injected rather than relying on clock/network state.

### Next user-priority milestone: keyboard-driven sight reading

The primary goal is to **read an unfamiliar note or phrase from the staff
and find it on the connected keyboard**, receiving immediate MIDI pitch
feedback without answer-revealing labels. The current repo has only fixed
notation examples and retrospective MIDI assessment; it does not implement
a live staff-reading practice loop. Keep this as a separately qualified
interactive feature with no hardware-pass claim until physical evidence
exists. See `docs/reading.md` and the dedicated GitHub issue.

Teacher-guided chord work now includes a small, comfortable wrist movement
cue, with credit to Shirly Mann; this is not an auto-assessed biomechanical
claim.

### Optional DAW environments

The piano-practice system will support a DAW-agnostic reading input contract,
with **REAPER for Linux** and **GarageBand for macOS** as candidate local sound,
metronome, and recording environments. No DAW API, plugin or private recording
is required for note identification. Concurrent MIDI port routing, octave
calibration, CC64 and physical-keyboard/DAW parity remain issue #2
acceptance work; see `docs/daw-routing.md`.
